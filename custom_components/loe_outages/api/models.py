"""Data models for LOE Lviv outages API."""

import datetime
from dataclasses import dataclass
from enum import StrEnum


class OutageEventType(StrEnum):
    """Outage event types."""

    DEFINITE = "Definite"


@dataclass(frozen=True)
class OutageEvent:
    """Represents an outage event."""

    event_type: OutageEventType
    start: datetime.datetime
    end: datetime.datetime


@dataclass(frozen=True)
class OutageSlot:
    """Represents an outage time slot template."""

    start: int  # Minutes from midnight
    end: int  # Minutes from midnight
    event_type: OutageEventType
