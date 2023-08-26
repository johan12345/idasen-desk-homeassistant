from typing import Any

from homeassistant.components.cover import CoverEntity, CoverEntityFeature, ATTR_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from . import IdasenData, IdasenDevice
from .const import DOMAIN, MOVEMENT_RANGE_CM


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform for LEDBLE."""
    data: IdasenData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        IdasenCover(data.coordinator, data.device, data.device.name),
    ])


class IdasenCover(CoordinatorEntity, CoverEntity):
    """Representation of a Idasen sensor."""
    def __init__(self, coordinator: DataUpdateCoordinator, device: IdasenDevice, name: str):
        super().__init__(coordinator)
        self._device = device

        self._attr_name = device.name
        self._attr_unique_id = device.address
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP |
            CoverEntityFeature.SET_POSITION
        )
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        device = self._device
        self._attr_current_cover_position = device.height / MOVEMENT_RANGE_CM * 100
        self._attr_is_closing = device.speed < 0
        self._attr_is_opening = device.speed > 0
        self._attr_is_closed = device.height == 0

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        await self._device.move_down()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open cover."""
        await self._device.move_up()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        pos = kwargs[ATTR_POSITION] / 100 * MOVEMENT_RANGE_CM
        await self._device.move_to(pos)

    async def async_stop_cover(self, **_kwargs: Any) -> None:
        """Stop the cover."""
        await self._device.move_stop()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            self._device.register_callback(self._handle_coordinator_update)
        )
        return await super().async_added_to_hass()
