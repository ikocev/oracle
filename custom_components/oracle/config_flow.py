"""Config flow for Oracle integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class OracleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Oracle."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title=user_input["host"], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required("host"): str,
                vol.Required("username", default=""): str,
                vol.Required("password", default=""): str,
                vol.Required("scan_interval", default=60): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OracleOptionsFlowHandler(config_entry)


class OracleOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Oracle."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = dict(self.config_entry.options)
        data_schema = vol.Schema(
            {
                vol.Required("scan_interval", default=current.get("scan_interval", 60)): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
