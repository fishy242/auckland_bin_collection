"""Auckland Bin Collection component."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM = Platform.SENSOR


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auckland Bin Collection as config entry."""

    hass.data.setdefault(DOMAIN, {})

    await hass.config_entries.async_forward_entry_setup(entry, PLATFORM)

    _LOGGER.debug("Auckland Bin Collection init entry setup")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry"""

    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, PLATFORM)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Auckland Bin Collection entry unloaded")

    return unload_ok
