"""Config flow for LOE Lviv Outages integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
)

from .const import AVAILABLE_GROUPS, CONF_GROUP, DOMAIN

LOGGER = logging.getLogger(__name__)


def get_config_value(
    entry: ConfigEntry | None,
    key: str,
    default: Any = None,
) -> Any:
    """Get a value from the config entry or default."""
    if entry is not None:
        return entry.options.get(key, entry.data.get(key, default))
    return default


def build_entry_title(data: dict[str, Any]) -> str:
    """Build a descriptive title from group."""
    return f"LOE Lviv Group {data[CONF_GROUP]}"


def build_group_schema(config_entry: ConfigEntry | None) -> vol.Schema:
    """Build the schema for the group selection step."""
    return vol.Schema(
        {
            vol.Required(
                CONF_GROUP,
                default=get_config_value(config_entry, CONF_GROUP),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=AVAILABLE_GROUPS,
                    translation_key="group",
                ),
            ),
        },
    )


class LoeOutagesOptionsFlow(OptionsFlow):
    """Handle options flow for LOE Lviv Outages."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the group change."""
        if user_input is not None:
            LOGGER.debug("Updating options: %s", user_input)
            # Update entry title along with options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=build_entry_title(user_input),
            )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=build_group_schema(self.config_entry),
        )


class LoeOutagesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LOE Lviv Outages."""

    VERSION = 3
    MINOR_VERSION = 0

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: ARG004
    ) -> LoeOutagesOptionsFlow:
        """Get the options flow for this handler."""
        return LoeOutagesOptionsFlow()

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            LOGGER.debug("Group selected: %s", user_input)
            title = build_entry_title(user_input)
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=build_group_schema(None),
        )
