"""Auckland Bin Collection config flow."""
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import CONF_LOCATION_ID, DOMAIN
from .sensor import async_get_bin_dates

_LOGGER = logging.getLogger(__name__)

_LOCATION_ID_LEN = 11

_E_NOT_DIGIT = "NOT DIGIT"
_E_INVALID_LEN = "INVALID LEN"
_E_NOT_FOUND = "NOT FOUND"

LOCATION_SCHEMA = vol.Schema({vol.Required(CONF_LOCATION_ID): str})


async def validate_location_id(hass: HomeAssistant, id: str) -> None:
    """validate the location ID input."""
    if not id.isdigit():
        raise ValueError(_E_NOT_DIGIT)

    if len(id) != _LOCATION_ID_LEN:
        raise ValueError(_E_INVALID_LEN)

    try:
        await async_get_bin_dates(hass, id)
    except ValueError as exc:
        raise ValueError(_E_NOT_FOUND) from exc


class AucklandBinCollectionFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Define Config Flow class."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            _loc: str = user_input[CONF_LOCATION_ID]

            try:
                await validate_location_id(self.hass, _loc)
            except ValueError as exc:
                if exc.args[0] in [_E_NOT_DIGIT, _E_INVALID_LEN]:
                    errors["base"] = "invalid_id"
                elif exc.args[0] in [_E_NOT_FOUND]:
                    errors["base"] = "not_found"

            if not errors:
                return self.async_create_entry(
                    title="Auckland Bin Collection",
                    data={CONF_LOCATION_ID: _loc},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=LOCATION_SCHEMA,
            errors=errors,
        )
