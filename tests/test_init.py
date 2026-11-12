"""Test component setup."""
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.setup import async_setup_component
import pytest

from custom_components.auckland_bin_collection.const import DOMAIN
from custom_components.auckland_bin_collection import (
    PLATFORMS,
    async_setup_entry,
    async_unload_entry,
)


@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


async def test_entry_starts_one_coordinator_before_platforms(hass):
    """Concurrent platform setup must share a single fetch and polling loop."""
    entry = MagicMock(entry_id="test_entry", data={"location_id": "12345678901"})
    coordinator = MagicMock(async_start=AsyncMock())

    async def forward_entry(config_entry, platforms):
        assert config_entry is entry
        assert platforms == PLATFORMS
        assert hass.data[DOMAIN][entry.entry_id] is coordinator
        coordinator.async_start.assert_awaited_once()

    with (
        patch(
            "custom_components.auckland_bin_collection.BinCollectionCoordinator",
            return_value=coordinator,
        ) as mock_coordinator,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=forward_entry,
        ),
    ):
        assert await async_setup_entry(hass, entry)

    mock_coordinator.assert_called_once_with(hass, "12345678901")


async def test_entry_unload_stops_shared_coordinator(hass):
    """Unloading cancels the only coordinator's pending refresh."""
    entry = MagicMock(entry_id="test_entry")
    coordinator = MagicMock(async_shutdown=AsyncMock())
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ):
        assert await async_unload_entry(hass, entry)

    coordinator.async_shutdown.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]
