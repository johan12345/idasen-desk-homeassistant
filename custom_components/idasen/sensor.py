from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LENGTH_CENTIMETERS, SPEED_METERS_PER_SECOND
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from . import IdasenData, IdasenDevice
from .const import DOMAIN, BASE_HEIGHT_CM


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform for LEDBLE."""
    data: IdasenData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        IdasenHeightSensor(data.coordinator, data.device, data.device.name),
        IdasenRelativeHeightSensor(data.coordinator, data.device, data.device.name),
        IdasenSpeedSensor(data.coordinator, data.device, entry.title)
    ])


class IdasenSensorBase(CoordinatorEntity, SensorEntity):
    """Representation of a Idasen sensor."""
    _attr_state_class = SensorStateClass.MEASUREMENT
    _sensor_name = None

    def __init__(self, coordinator: DataUpdateCoordinator, device: IdasenDevice, name: str):
        super().__init__(coordinator)
        self._device = device

        self._attr_name = f"{device.name} {self._sensor_name}"
        self._attr_unique_id = f"{device.address}-{self._sensor_name}"
        self._async_update_attrs()

    def _async_update_attrs(self) -> None:
        pass

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            self._device.register_callback(self._handle_coordinator_update)
        )
        return await super().async_added_to_hass()


class IdasenHeightSensor(IdasenSensorBase):
    _attr_native_unit_of_measurement = LENGTH_CENTIMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _sensor_name = "Height"

    @callback
    def _async_update_attrs(self) -> None:
        device = self._device
        self._attr_native_value = device.state.height + BASE_HEIGHT_CM

class IdasenRelativeHeightSensor(IdasenSensorBase):
    _attr_native_unit_of_measurement = LENGTH_CENTIMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _sensor_name = "Relative Height"

    @callback
    def _async_update_attrs(self) -> None:
        device = self._device
        self._attr_native_value = device.state.height

class IdasenSpeedSensor(IdasenSensorBase):
    _attr_native_unit_of_measurement = SPEED_METERS_PER_SECOND
    _attr_device_class = SensorDeviceClass.SPEED
    _sensor_name = "Speed"

    @callback
    def _async_update_attrs(self) -> None:
        device = self._device
        self._attr_native_value = device.state.speed



