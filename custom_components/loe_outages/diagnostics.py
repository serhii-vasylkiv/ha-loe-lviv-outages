"""
Diagnostics support for LOE Lviv Outages.

Learn more about diagnostics:
https://developers.home-assistant.io/docs/core/integration_diagnostics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import CONF_GROUP

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import LoeOutagesConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: LoeOutagesConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    api = entry.runtime_data.api
    data = entry.data

    # Build diagnostics safely, handling None values
    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "domain": entry.domain,
            "title": entry.title,
            "state": str(entry.state),
            "data": {
                "group": data.get(CONF_GROUP),
            },
            "options": {
                "group": entry.options.get(CONF_GROUP),
            },
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "group": coordinator.group,
            "current_state": coordinator.current_state,
            "schedule_updated_on": (
                coordinator.schedule_updated_on.isoformat()
                if coordinator.schedule_updated_on
                else None
            ),
            "next_outage": (
                coordinator.next_outage.isoformat() if coordinator.next_outage else None
            ),
            "next_connectivity": (
                coordinator.next_connectivity.isoformat()
                if coordinator.next_connectivity
                else None
            ),
        },
        "api": {
            "group": api.group,
            "schedule_date": str(api.schedule_date) if api.schedule_date else None,
            "updated_on": api.updated_on.isoformat() if api.updated_on else None,
            "schedule_text": api.schedule_text[:500] if api.schedule_text else None,
            "schedule_text_length": (
                len(api.schedule_text) if api.schedule_text else 0
            ),
            "group_schedules": {
                group: [(start, end) for start, end in ranges]
                for group, ranges in api.group_schedules.items()
            },
            "raw_data_keys": list(api.raw_data.keys()) if api.raw_data else None,
            "raw_data_sample": (str(api.raw_data)[:1000] if api.raw_data else None),
        },
        "error": {
            "last_exception": (
                str(coordinator.last_exception) if coordinator.last_exception else None
            ),
        },
    }
