"""Init file for LOE Lviv Outages integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration

from .api import LoeApi
from .const import CONF_GROUP
from .coordinator import LoeOutagesCoordinator
from .data import LoeOutagesData

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .data import LoeOutagesConfigEntry

LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry to new version."""
    LOGGER.info(
        "Migrating entry %s from version %s",
        entry.entry_id,
        entry.version,
    )

    # Migration from Yasno (v1, v2) to LOE Lviv (v3)
    if entry.version < 3:  # noqa: PLR2004
        updated_data = {CONF_GROUP: entry.data.get(CONF_GROUP)}
        updated_options = {}

        # Preserve group from options if it exists
        if CONF_GROUP in entry.options:
            updated_options[CONF_GROUP] = entry.options[CONF_GROUP]

        # Update entry with new data and version
        hass.config_entries.async_update_entry(
            entry,
            data=updated_data,
            options=updated_options,
            version=3,
        )

        LOGGER.info("Migration to version 3 complete")

    LOGGER.info("Entry %s now at version %s", entry.entry_id, entry.version)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LoeOutagesConfigEntry,
) -> bool:
    """Set up a new entry."""
    LOGGER.info("Setup entry: %s", entry)

    # Validate required keys are present
    group = entry.options.get(CONF_GROUP, entry.data.get(CONF_GROUP))

    if not group:
        LOGGER.error(
            "Missing required group for entry %s",
            entry.entry_id,
        )
        return False

    api = LoeApi(group=group)
    coordinator = LoeOutagesCoordinator(hass, entry, api)
    entry.runtime_data = LoeOutagesData(
        api=api,
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    # First refresh
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: LoeOutagesConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: LoeOutagesConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    LOGGER.info("Unload entry: %s", entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
