"""Test for Auckland Bin Collection calendar."""
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from freezegun import freeze_time
import pytest
import pytz
from homeassistant.components.calendar import CalendarEvent

from custom_components.auckland_bin_collection.calendar import (
    AucklandBinCollectionCalendar,
    async_setup_entry,
)
from custom_components.auckland_bin_collection.const import DOMAIN

TEST_LOC = "12345678901"
TEST_UPCOMING_DATE_STR = "Tuesday, 12 January"
TEST_UPCOMING_TYPE_STR = ["Rubbish", "Food scraps"]

TEST_NEXT_DATE_STR = "Friday, 25 March"
TEST_NEXT_TYPE_STR = ["Rubbish", "Recycling"]

TEST_COORDINATOR_DATA = [
    {TEST_UPCOMING_DATE_STR: TEST_UPCOMING_TYPE_STR},
    {TEST_NEXT_DATE_STR: TEST_NEXT_TYPE_STR},
]


@pytest.mark.asyncio
async def test_async_setup_entry(hass):
    """Test calendar platform setup."""
    mock_entry = MagicMock()
    mock_entry.data = {"location_id": TEST_LOC}
    mock_entry.entry_id = "test_entry"

    hass.data.setdefault(DOMAIN, {})

    added_entities = []
    def capture_entities(entities):
        added_entities.extend(entities)

    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            return_value=[["dummy"]],
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ),
    ):
        await async_setup_entry(hass, mock_entry, capture_entities)

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], AucklandBinCollectionCalendar)
    assert "test_entry" in hass.data[DOMAIN]


@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_calendar_next_event():
    """Test the event property returns the single next immediate event."""
    m_coordinator = AsyncMock()
    m_coordinator.data = TEST_COORDINATOR_DATA

    calendar = AucklandBinCollectionCalendar(m_coordinator, TEST_LOC)
    event = calendar.event

    assert isinstance(event, CalendarEvent)
    # The first bin type of the first day
    assert event.summary == "Rubbish"
    assert event.start == date(2023, 1, 12)
    assert event.end == date(2023, 1, 13)


@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_calendar_async_get_events():
    """Test returning separate events for each bin type in the time range."""
    m_coordinator = AsyncMock()
    m_coordinator.data = TEST_COORDINATOR_DATA

    calendar = AucklandBinCollectionCalendar(m_coordinator, TEST_LOC)

    nz_tz = pytz.timezone("Pacific/Auckland")
    
    # Query covering both dates
    start_date = nz_tz.localize(datetime(2023, 1, 1))
    end_date = nz_tz.localize(datetime(2023, 12, 31))

    # We mock out hass safely
    mock_hass = MagicMock()
    events = await calendar.async_get_events(mock_hass, start_date, end_date)

    # 2 on 12 Jan + 2 on 25 March = 4 events
    assert len(events) == 4

    # Check 12 Jan
    assert events[0].summary == "Rubbish"
    assert events[0].start == date(2023, 1, 12)
    
    assert events[1].summary == "Food scraps"
    assert events[1].start == date(2023, 1, 12)
    
    # Check 25 March
    assert events[2].summary == "Rubbish"
    assert events[2].start == date(2023, 3, 25)
    
    assert events[3].summary == "Recycling"
    assert events[3].start == date(2023, 3, 25)

@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_calendar_empty_data():
    """Test event property and async_get_events handles empty coordinator data."""
    m_coordinator = AsyncMock()
    m_coordinator.data = []

    calendar = AucklandBinCollectionCalendar(m_coordinator, TEST_LOC)
    
    assert calendar.event is None
    
    nz_tz = pytz.timezone("Pacific/Auckland")
    start_date = nz_tz.localize(datetime(2023, 1, 1))
    end_date = nz_tz.localize(datetime(2023, 12, 31))
    
    events = await calendar.async_get_events(MagicMock(), start_date, end_date)
    assert len(events) == 0

