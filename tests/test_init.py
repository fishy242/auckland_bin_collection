"""Test component setup."""
from homeassistant.setup import async_setup_component
import pytest

from custom_components.auckland_bin_collection.const import DOMAIN


@pytest.mark.asyncio
async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True
