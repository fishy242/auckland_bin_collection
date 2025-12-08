"""Test for the config flow."""
from unittest import mock
from unittest.mock import patch

import pytest

from custom_components.auckland_bin_collection import config_flow
from custom_components.auckland_bin_collection.const import CONF_LOCATION_ID


@pytest.mark.asyncio
@patch("custom_components.auckland_bin_collection.config_flow.async_get_bin_dates")
async def test_validate_location_id(mock_async_get_bin_dates, hass):
    """Test valid location id."""

    mock_async_get_bin_dates.return_value = [{"Monday January 1": ["Rubbish"]}]
    await config_flow.validate_location_id(hass, "12345678901")


@pytest.mark.asyncio
async def test_validate_location_id_non_digit(hass):
    """Test non-digit location id."""
    with pytest.raises(ValueError) as exc:
        await config_flow.validate_location_id(hass, "abcdefghijk")
    assert str(exc.value) == config_flow._E_NOT_DIGIT


@pytest.mark.asyncio
async def test_validate_location_id_invalid_len(hass):
    """Test invalid length of location id."""
    with pytest.raises(ValueError) as exc:
        await config_flow.validate_location_id(hass, "12345")
    assert str(exc.value) == config_flow._E_INVALID_LEN


@pytest.mark.asyncio
@patch("custom_components.auckland_bin_collection.config_flow.async_get_bin_dates")
async def test_validate_location_id_not_found(mock_async_get_bin_dates, hass):
    """Test location ID not found."""
    mock_async_get_bin_dates.side_effect = ValueError()
    with pytest.raises(ValueError) as exc:
        await config_flow.validate_location_id(hass, "12345678901")
    assert str(exc.value) == config_flow._E_NOT_FOUND


@pytest.mark.asyncio
async def test_flow_user_init(hass):
    """Test the initialization of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    # Check required fields - handle version differences
    assert result["data_schema"] == config_flow.LOCATION_SCHEMA
    assert result["description_placeholders"] is None
    assert result["errors"] == {}
    assert "flow_id" in result
    assert result["handler"] == "auckland_bin_collection"
    assert result["last_step"] is None
    assert result["step_id"] == "user"
    # Type can be string or enum depending on version
    assert str(result["type"]) == "form"


@pytest.mark.asyncio
@patch("custom_components.auckland_bin_collection.config_flow.validate_location_id")
async def test_flow_location_id_non_digit(mock_validate_location_id, hass):
    """Test errors populated when location ID is non digit."""
    mock_validate_location_id.side_effect = ValueError(config_flow._E_NOT_DIGIT)

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_LOCATION_ID: "abcdefghijk"}
    )
    assert {"base": "invalid_id"} == result["errors"]


@pytest.mark.asyncio
@patch("custom_components.auckland_bin_collection.config_flow.validate_location_id")
async def test_flow_location_id_invalid_len(mock_validate_location_id, hass):
    """Tets errors populated when location ID has invalid length."""
    mock_validate_location_id.side_effect = ValueError(config_flow._E_INVALID_LEN)

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_LOCATION_ID: "12345"}
    )
    assert {"base": "invalid_id"} == result["errors"]


@pytest.mark.asyncio
@patch("custom_components.auckland_bin_collection.config_flow.validate_location_id")
async def test_flow_location_id_not_found(mock_validate_location_id, hass):
    """Test errors populated when location ID not found."""
    mock_validate_location_id.side_effect = ValueError(config_flow._E_NOT_FOUND)

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_LOCATION_ID: "12345678901"}
    )
    assert {"base": "not_found"} == result["errors"]
