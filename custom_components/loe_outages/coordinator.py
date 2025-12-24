"""Data coordinator for LOE Lviv Outages integration."""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_utils

from .api import LoeApi, OutageEvent, OutageEventType
from .const import (
    CONF_GROUP,
    DOMAIN,
    OUTAGE_LOOKAHEAD,
    OUTAGE_TEXT_FALLBACK,
    STATE_NORMAL,
    STATE_OUTAGE,
    TRANSLATION_KEY_EVENT_OUTAGE,
    UPDATE_INTERVAL,
)
from .helpers import merge_consecutive_outages

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

EVENT_TYPE_STATE_MAP: dict[OutageEventType, str] = {
    OutageEventType.DEFINITE: STATE_OUTAGE,
}


def find_next_outage(
    events: list[OutageEvent],
    now: datetime.datetime,
) -> OutageEvent | None:
    """Find the next outage event that starts after the given time."""
    for event in events:
        if event.start > now:
            return event
    return None


class LoeOutagesCoordinator(DataUpdateCoordinator):
    """Class to manage fetching LOE Lviv outages data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: LoeApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(minutes=UPDATE_INTERVAL),
        )
        self.hass = hass
        self.config_entry = config_entry
        self.translations = {}

        # Get configuration values
        self.group = config_entry.options.get(
            CONF_GROUP,
            config_entry.data.get(CONF_GROUP),
        )

        if not self.group:
            group_required_msg = (
                "Group not set in configuration - this should not happen "
                "with proper config flow"
            )
            group_error = "Group configuration is required"
            LOGGER.error(group_required_msg)
            raise ValueError(group_error)

        # Use the provided API instance
        self.api = api

    async def _async_update_data(self) -> None:
        """Fetch data from LOE API."""
        await self.async_fetch_translations()

        # Fetch schedule data
        try:
            await self.api.fetch_data()
        except Exception as err:
            msg = f"Failed to fetch schedule data: {err}"
            raise UpdateFailed(msg) from err

    def _event_to_state(self, event: OutageEvent | None) -> str:
        """Map outage event to electricity state."""
        if not event:
            return STATE_NORMAL
        return EVENT_TYPE_STATE_MAP.get(event.event_type, STATE_UNKNOWN)

    async def async_fetch_translations(self) -> None:
        """Fetch translations."""
        self.translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "common",
            [DOMAIN],
        )

    @property
    def event_summary(self) -> str:
        """Return localized summary with fallback."""
        return self.translations.get(TRANSLATION_KEY_EVENT_OUTAGE, OUTAGE_TEXT_FALLBACK)

    @property
    def current_event(self) -> OutageEvent | None:
        """Get the current event."""
        try:
            return self.api.get_current_event(dt_utils.now())
        except Exception:  # noqa: BLE001
            LOGGER.warning(
                "Failed to get current event, sensors will show unknown state",
                exc_info=True,
            )
            return None

    @property
    def current_state(self) -> str:
        """Get the current state."""
        return self._event_to_state(self.current_event)

    @property
    def schedule_updated_on(self) -> datetime.datetime | None:
        """Get the schedule last updated timestamp."""
        return self.api.get_schedule_updated_on()

    @property
    def next_outage(self) -> datetime.date | datetime.datetime | None:
        """Get the next outage time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            now,
            OUTAGE_LOOKAHEAD,
        )

        if event := find_next_outage(events, now):
            LOGGER.debug("Next outage: %s", event)
            return event.start

        return None

    @property
    def next_connectivity(self) -> datetime.date | datetime.datetime | None:
        """Get next connectivity time."""
        now = dt_utils.now()
        events = self.get_merged_outages(
            now,
            OUTAGE_LOOKAHEAD,
        )

        # Check if we are in an outage
        for event in events:
            if event.start <= now < event.end:
                return event.end

        # Find next outage
        if event := find_next_outage(events, now):
            LOGGER.debug("Next connectivity event: %s", event)
            return event.end

        return None

    def get_outage_at(
        self,
        at: datetime.datetime,
    ) -> OutageEvent | None:
        """Get an outage event at a given time."""
        try:
            return self.api.get_current_event(at)
        except Exception:  # noqa: BLE001
            LOGGER.warning("Failed to get current outage", exc_info=True)
            return None

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get outage events within the date range."""
        try:
            events = self.api.get_events_between(start_date, end_date)
        except Exception:  # noqa: BLE001
            LOGGER.warning(
                'Failed to get events between "%s" -> "%s"',
                start_date,
                end_date,
                exc_info=True,
            )
            return []

        return sorted(events, key=lambda event: event.start)

    def get_merged_outages(
        self,
        start_date: datetime.datetime,
        lookahead_days: int,
    ) -> list[OutageEvent]:
        """Get merged outage events for a lookahead period."""
        end_date = start_date + datetime.timedelta(days=lookahead_days)
        events = self.get_events_between(start_date, end_date)
        return merge_consecutive_outages(events)
