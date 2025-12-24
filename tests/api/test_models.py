"""Tests for LOE Lviv Outages models."""

import datetime

import pytest

from custom_components.loe_outages.api.models import (
    OutageEvent,
    OutageEventType,
    OutageSlot,
)


class TestOutageEventType:
    """Test OutageEventType enum."""

    def test_definite(self):
        """Test DEFINITE type."""
        assert OutageEventType.DEFINITE == "Definite"


class TestOutageEvent:
    """Test OutageEvent dataclass."""

    def test_create_event(self):
        """Test creating an outage event."""
        start = datetime.datetime(2025, 1, 27, 10, 0, 0)
        end = datetime.datetime(2025, 1, 27, 12, 0, 0)
        event = OutageEvent(
            event_type=OutageEventType.DEFINITE,
            start=start,
            end=end,
        )
        assert event.start == start
        assert event.end == end
        assert event.event_type == OutageEventType.DEFINITE

    def test_frozen(self):
        """Test that event is frozen."""
        event = OutageEvent(
            event_type=OutageEventType.DEFINITE,
            start=datetime.datetime(2025, 1, 27, 10, 0, 0),
            end=datetime.datetime(2025, 1, 27, 12, 0, 0),
        )
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            event.start = datetime.datetime(2025, 1, 28, 10, 0, 0)


class TestOutageSlot:
    """Test OutageSlot dataclass."""

    def test_create_slot(self):
        """Test creating an outage slot."""
        slot = OutageSlot(
            start=960,
            end=1200,
            event_type=OutageEventType.DEFINITE,
        )
        assert slot.start == 960
        assert slot.end == 1200
        assert slot.event_type == OutageEventType.DEFINITE

    def test_frozen(self):
        """Test that slot is frozen."""
        slot = OutageSlot(
            start=960,
            end=1200,
            event_type=OutageEventType.DEFINITE,
        )
        with pytest.raises(AttributeError):
            # noinspection PyDataclass
            slot.start = 1000
