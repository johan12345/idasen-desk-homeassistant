import asyncio
import logging
import struct
from dataclasses import dataclass
from typing import Callable

from bleak import BLEDevice, AdvertisementData, BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import UUID_HEIGHT, UUID_COMMAND, COMMAND_UP, COMMAND_DOWN, COMMAND_STOP, COMMAND_REFERENCE_INPUT_STOP, \
    UUID_REFERENCE_INPUT

_LOGGER = logging.getLogger(__name__)
DISCONNECT_DELAY = 120

def to_native(cm):
    return int(cm * 100)


def to_cm(native):
    return int(native) / 100


def to_meters_per_second(native):
    return int(native) * 6.14e-6  # empirical value, assuming the Idasen desk's maximum speed is ~1.5 inch/s


@dataclass(frozen=True)
class IdasenState:
    height: float
    speed: float


class IdasenDevice:
    """Data for Idasen BLE sensors."""

    def __init__(self, ble_device: BLEDevice) -> None:
        super().__init__()
        self._ble_device = ble_device
        self._advertisement_data = None
        self._state = IdasenState(0, 0)
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self.loop = asyncio.get_running_loop()
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._callbacks: list[Callable[[IdasenState], None]] = []
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._expected_disconnect = False
        self._client: BleakClientWithServiceCache | None = None
        self._stop_event = asyncio.Event()
        self._move_lock = asyncio.Lock()

    def set_ble_device_and_advertisement_data(self, ble_device: BLEDevice, advertisement_data: AdvertisementData):
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data

    @property
    def address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def _address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._ble_device.name or self._ble_device.address

    @property
    def rssi(self) -> int | None:
        """Get the rssi of the device."""
        if self._advertisement_data:
            return self._advertisement_data.rssi
        return None

    @property
    def state(self):
        return self._state

    @property
    def height(self):
        return self._state.height

    @property
    def speed(self):
        return self._state.speed

    async def update(self) -> None:
        """Update from BLE advertisement data."""
        await self._ensure_connected()
        _LOGGER.debug("%s: Updating", self.name)

        data = await self._client.read_gatt_char(UUID_HEIGHT)
        self._update_state(data)

        _LOGGER.debug("Successfully read active gatt characters")

    async def move_up(self):
        await self.move_stop()
        await self._move_lock.acquire()
        try:
            while not self._stop_event.is_set():
                await self._client.write_gatt_char(UUID_COMMAND, COMMAND_UP, response=False)
                await asyncio.sleep(0.5)
        finally:
            self._move_lock.release()

    async def move_down(self):
        await self.move_stop()
        await self._move_lock.acquire()
        try:
            while not self._stop_event.is_set():
                await self._client.write_gatt_char(UUID_COMMAND, COMMAND_DOWN, response=False)
                await asyncio.sleep(0.5)
        finally:
            self._move_lock.release()

    async def move_stop(self):
        self._stop_event.set()
        await self._move_lock.acquire()
        self._stop_event.clear()
        try:
            await self._ensure_connected()
            await self._client.write_gatt_char(UUID_COMMAND, COMMAND_STOP, response=False)
            await self._client.write_gatt_char(UUID_REFERENCE_INPUT, COMMAND_REFERENCE_INPUT_STOP, response=False)
        finally:
            self._move_lock.release()

    async def move_to(self, target):
        await self.move_stop()
        await self._move_lock.acquire()

        encoded_target = bytearray(struct.pack("<H", to_native(target)))
        try:
            while not self._stop_event.is_set():
                await self._client.write_gatt_char(UUID_REFERENCE_INPUT, encoded_target, response=False)
                await asyncio.sleep(0.5)
                if self._state.speed == 0:
                    break
        finally:
            self._move_lock.release()


    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._ble_device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            resolved = self._resolve_characteristics(client.services)
            if not resolved:
                # Try to handle services failing to load
                resolved = self._resolve_characteristics(await client.get_services())

            self._client = client
            self._reset_disconnect_timer()

            _LOGGER.debug(
                "%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi
            )
            await client.start_notify(self._read_char, self._notification_handler)

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Handle notification responses."""
        _LOGGER.debug("%s: Notification received: %s", self.name, data.hex())
        self._update_state(data)

    def _update_state(self, data):
        pos, speed = struct.unpack("<Hh", data)
        self._state = IdasenState(to_cm(pos), to_meters_per_second(speed))
        self._fire_callbacks()

    def _reset_disconnect_timer(self) -> None:
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnect(self) -> None:
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            read_char = self._read_char
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._read_char = None
            self._write_char = None
            if client and client.is_connected:
                await client.stop_notify(read_char)
                await client.disconnect()

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        _LOGGER.warning(
            "%s: Device unexpectedly disconnected; RSSI: %s",
            self.name,
            self.rssi,
        )

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Resolve characteristics."""
        for characteristic in [UUID_HEIGHT]:
            if char := services.get_characteristic(characteristic):
                self._read_char = char
                break
        for characteristic in [UUID_COMMAND]:
            if char := services.get_characteristic(characteristic):
                self._write_char = char
                break
        return bool(self._read_char and self._write_char)

    def register_callback(
            self, callback: Callable[[IdasenState], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._callbacks.remove(callback)

        self._callbacks.append(callback)
        return unregister_callback

    def _fire_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._callbacks:
            callback(self._state)

    async def stop(self) -> None:
        """Stop the Idasen."""
        _LOGGER.debug("%s: Stop", self.name)
        await self._execute_disconnect()