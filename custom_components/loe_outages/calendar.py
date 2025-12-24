"""Calendar platform for LOE Lviv outages integration."""

import datetime
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_utils

from .api import OutageEvent
from .coordinator import LoeOutagesCoordinator
from .data import LoeOutagesConfigEntry
from .entity import LoeOutagesEntity
from .helpers import merge_consecutive_outages

LOGGER = logging.getLogger(__name__)


def to_calendar_event(
    coordinator: LoeOutagesCoordinator,
    event: OutageEvent,
) -> CalendarEvent:
    """Convert OutageEvent into Home Assistant CalendarEvent."""
    summary = coordinator.event_summary
    calendar_event = CalendarEvent(
        summary=summary,
        start=event.start,
        end=event.end,
        description=event.event_type.value,
        uid=f"outage-{event.start.isoformat()}",
    )
    LOGGER.debug("Calendar Event: %s", calendar_event)
    return calendar_event


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: LoeOutagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the LOE Lviv outages calendar platform."""
    LOGGER.debug("Setup new entry: %s", config_entry)
    coordinator = config_entry.runtime_data.coordinator
    async_add_entities([LoeOutagesCalendar(coordinator)])


class LoeOutagesCalendar(LoeOutagesEntity, CalendarEntity):
    """Implementation of LOE outages calendar entity."""

    def __init__(
        self,
        coordinator: LoeOutagesCoordinator,
    ) -> None:
        """Initialize the LoeOutagesCalendar entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(
            key="outages",
            name="Outages",
            translation_key="outages",
        )
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}-"
            f"{coordinator.group}-"
            f"{self.entity_description.key}"
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event or None."""
        LOGGER.debug("Getting event at now")
        outage_event = self.coordinator.get_outage_at(dt_utils.now())
        if not outage_event:
            return None
        return to_calendar_event(self.coordinator, outage_event)

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        LOGGER.debug('Getting events between "%s" -> "%s"', start_date, end_date)
        events = self.coordinator.get_events_between(start_date, end_date)
        events = merge_consecutive_outages(events)

        return [to_calendar_event(self.coordinator, event) for event in events]
