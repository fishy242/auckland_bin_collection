"""Auckland Bin Collection component."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LOCATION_ID, DOMAIN
from .sensor import BinCollectionCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auckland Bin Collection as config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Platforms are forwarded concurrently. Create their shared coordinator here
    # so the sensor and calendar cannot each start a separate polling loop.
    coordinator = BinCollectionCoordinator(hass, entry.data[CONF_LOCATION_ID])
    await coordinator.async_start()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Auckland Bin Collection init entry setup")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry"""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            # Cancel the scheduled poll callback so it stops holding a
            # reference to the coordinator after unload/reload.
            await coordinator.async_shutdown()
        _LOGGER.debug("Auckland Bin Collection entry unloaded")

    return unload_ok
