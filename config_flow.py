"""Auckland Bin Collection config flow."""
import logging
import voluptuous as vol
from typing import Any
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_LOCATION_ID


class AucklandBinCollectionFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Define Config Flow class."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Auckland Bin Collection",
                data={CONF_LOCATION_ID: user_input[CONF_LOCATION_ID]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_LOCATION_ID): str}),
        )
