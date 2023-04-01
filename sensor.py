"""Auckland Bin Collection sensor component"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import CONF_LOCATION_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Auckland Bin Collection entities from a config_entry."""
    location_id = entry.data[CONF_LOCATION_ID]

    async_add_entities([AucklandBinCollection("Next Collection", location_id)])


class AucklandBinCollection(SensorEntity):
    """AucklandBinCollection class."""

    def __init__(self, name, location_id) -> None:
        self._name = name
        self._location_id = location_id

    @property
    def name(self):
        return self._name

    @property
    def native_value(self):
        """Return the state."""
        return self._location_id

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"attr": "I am attribute"}

    async def async_update(self):
        """Handle data update."""
        _LOGGER.debug("async_update called!")
