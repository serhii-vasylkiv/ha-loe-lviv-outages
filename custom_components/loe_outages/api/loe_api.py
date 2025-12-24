"""LOE Lviv outages API."""

import datetime
import logging
import re
from html import unescape

import aiohttp

from .const import LOE_API_ENDPOINT
from .models import OutageEvent, OutageEventType

LOGGER = logging.getLogger(__name__)

# Regex patterns for parsing Ukrainian schedule text
DATE_PATTERN = r"Графік погодинних відключень на (\d{2}\.\d{2}\.\d{4})"
UPDATE_PATTERN = r"Інформація станом на (\d{2}:\d{2}) (\d{2}\.\d{2}\.\d{4})"
GROUP_PATTERN = r"Група (\d\.\d)\.\s*Електроенергії немає\s+(.+?)\."
TIME_RANGE_PATTERN = r"з (\d{2}:\d{2}) до (\d{2}:\d{2})"


class LoeApi:
    """API for fetching LOE Lviv outages data."""

    def __init__(self, group: str | None = None) -> None:
        """Initialize the LoeApi."""
        self.group = group
        self.raw_data = None
        self.schedule_text = None
        self.schedule_date = None
        self.updated_on = None
        self.group_schedules = {}

    async def _get_data(
        self,
        session: aiohttp.ClientSession,
        url: str,
        timeout_secs: int = 60,
    ) -> dict | None:
        """Fetch data from the given URL."""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout_secs),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            LOGGER.exception("Error fetching data from %s", url)
            return None

    async def fetch_schedule_data(self) -> None:
        """Fetch schedule data from LOE API."""
        async with aiohttp.ClientSession() as session:
            self.raw_data = await self._get_data(session, LOE_API_ENDPOINT)

        if self.raw_data:
            self._extract_schedule_text()
            if self.schedule_text:
                self._parse_schedule_text()

    def _extract_schedule_text(self) -> None:
        """Extract schedule text from JSON response."""
        if not self.raw_data:
            return

        try:
            # API returns: {"hydra:member": [{"menuItems": [{"rawHtml": "..."}]}]}
            members = self.raw_data.get("hydra:member", [])
            if members and len(members) > 0:
                menu_items = members[0].get("menuItems", [])
                if menu_items and len(menu_items) > 0:
                    # First menuItem is "Today" with rawHtml field
                    raw_html = menu_items[0].get("rawHtml", "")
                    # Remove HTML tags and decode entities
                    text = re.sub(r"<[^>]+>", " ", raw_html)
                    text = unescape(text)
                    # Clean up whitespace
                    text = re.sub(r"\s+", " ", text).strip()
                    self.schedule_text = text
                    LOGGER.debug("Extracted schedule text: %s", text[:200])
        except (KeyError, IndexError, TypeError) as err:
            LOGGER.warning("Failed to extract schedule text: %s", err)
            self.schedule_text = None

    def _parse_schedule_text(self) -> None:
        """Parse schedule text to extract events."""
        if not self.schedule_text:
            return

        # Extract schedule date
        date_match = re.search(DATE_PATTERN, self.schedule_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                self.schedule_date = datetime.datetime.strptime(  # noqa: DTZ007
                    date_str, "%d.%m.%Y"
                ).date()
                LOGGER.debug("Parsed schedule date: %s", self.schedule_date)
            except ValueError as err:
                LOGGER.warning("Failed to parse date %s: %s", date_str, err)
                self.schedule_date = None
        else:
            LOGGER.warning("Schedule date not found in text")
            self.schedule_date = None

        # Extract update timestamp
        update_match = re.search(UPDATE_PATTERN, self.schedule_text)
        if update_match:
            time_str = update_match.group(1)
            date_str = update_match.group(2)
            try:
                # Parse as naive datetime and assume Europe/Kiev timezone
                naive_dt = datetime.datetime.strptime(  # noqa: DTZ007
                    f"{date_str} {time_str}", "%d.%m.%Y %H:%M"
                )
                # Add timezone info (Europe/Kiev is UTC+2/UTC+3 with DST)
                # Using replace with a fixed offset for simplicity
                import zoneinfo  # noqa: PLC0415

                kiev_tz = zoneinfo.ZoneInfo("Europe/Kiev")
                self.updated_on = naive_dt.replace(tzinfo=kiev_tz)
                LOGGER.debug("Parsed update time: %s", self.updated_on)
            except (ValueError, ImportError) as err:
                LOGGER.warning(
                    "Failed to parse update time %s %s: %s", time_str, date_str, err
                )
                self.updated_on = None
        else:
            LOGGER.warning("Update time not found in text")
            self.updated_on = None

        # Extract group schedules
        self.group_schedules = {}
        for group_match in re.finditer(GROUP_PATTERN, self.schedule_text):
            group_num = group_match.group(1)
            time_ranges_text = group_match.group(2)

            # Parse time ranges for this group
            time_ranges = []
            for time_match in re.finditer(TIME_RANGE_PATTERN, time_ranges_text):
                start_str = time_match.group(1)
                end_str = time_match.group(2)
                time_ranges.append((start_str, end_str))

            self.group_schedules[group_num] = time_ranges
            LOGGER.debug("Parsed group %s: %s ranges", group_num, len(time_ranges))

    def _time_str_to_minutes(self, time_str: str) -> int:
        """Convert time string HH:MM to minutes since midnight."""
        hours, minutes = map(int, time_str.split(":"))
        return hours * 60 + minutes

    def _minutes_to_datetime(
        self, minutes: int, date: datetime.date
    ) -> datetime.datetime:
        """Convert minutes from start of day to datetime with Europe/Kiev timezone."""
        import zoneinfo  # noqa: PLC0415

        hours = minutes // 60
        mins = minutes % 60
        kiev_tz = zoneinfo.ZoneInfo("Europe/Kiev")

        # Handle end of day (24:00) - use midnight of next day
        if hours == 24:  # noqa: PLR2004
            next_day = date + datetime.timedelta(days=1)
            naive_dt = datetime.datetime.combine(next_day, datetime.time(0, 0))
        else:
            naive_dt = datetime.datetime.combine(date, datetime.time(hours, mins))

        # Make timezone-aware
        return naive_dt.replace(tzinfo=kiev_tz)

    def get_events_for_group(self, group: str) -> list[OutageEvent]:
        """Get outage events for a specific group."""
        if not self.schedule_date or group not in self.group_schedules:
            return []

        events = []
        time_ranges = self.group_schedules[group]

        for start_str, end_str in time_ranges:
            try:
                start_minutes = self._time_str_to_minutes(start_str)
                end_minutes = self._time_str_to_minutes(end_str)

                # Handle time range crossing midnight
                if end_minutes < start_minutes or end_str == "24:00":
                    end_minutes = 1440  # End of day

                start_dt = self._minutes_to_datetime(start_minutes, self.schedule_date)
                end_dt = self._minutes_to_datetime(end_minutes, self.schedule_date)

                events.append(
                    OutageEvent(
                        event_type=OutageEventType.DEFINITE,
                        start=start_dt,
                        end=end_dt,
                    )
                )
            except (ValueError, AttributeError) as err:
                LOGGER.warning(
                    "Failed to parse time range %s-%s: %s", start_str, end_str, err
                )
                continue

        return sorted(events, key=lambda e: e.start)

    def get_current_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the current outage event at a given time."""
        if not self.group:
            return None

        events = self.get_events_for_group(self.group)
        for event in events:
            if event.start <= at < event.end:
                return event
        return None

    def get_next_event(self, at: datetime.datetime) -> OutageEvent | None:
        """Get the next outage event after a given time."""
        if not self.group:
            return None

        events = self.get_events_for_group(self.group)
        for event in events:
            if event.start > at:
                return event
        return None

    def get_events_between(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[OutageEvent]:
        """Get all outage events within the date range."""
        if not self.group:
            return []

        events = self.get_events_for_group(self.group)

        # Filter events that intersect with the requested range
        return [
            event
            for event in events
            if (
                start_date <= event.start <= end_date
                or start_date <= event.end <= end_date
                or event.start <= start_date <= event.end
                or event.start <= end_date <= event.end
            )
        ]

    def get_schedule_updated_on(self) -> datetime.datetime | None:
        """Get the timestamp when the schedule was last updated."""
        return self.updated_on

    async def fetch_data(self) -> None:
        """Fetch all required data."""
        await self.fetch_schedule_data()
