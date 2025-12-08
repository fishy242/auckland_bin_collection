"""Test for Auckland Bin Collection sensor."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from freezegun import freeze_time
import pytest

from custom_components.auckland_bin_collection.sensor import (
    URL_REQUEST,
    AucklandBinCollection,
    get_date_from_str,
)

TEST_LOC = "12345678901"
TEST_UPCOMING_DATE_STR = "Tuesday, 12 January"
TEST_UPCOMING_TYPE_STR = ["Rubbish", "Food scraps"]
TEST_UPCOMING_STATE = "2023-01-12"
TEST_UPCOMING_RUBBISH = "true"
TEST_UPCOMING_RECYCLE = "false"
TEST_UPCOMING_FOODSCRAPS = "true"
TEST_UPCOMING_ATTRS = {
    "location_id": TEST_LOC,
    "date": TEST_UPCOMING_DATE_STR,
    "rubbish": TEST_UPCOMING_RUBBISH,
    "recycle": TEST_UPCOMING_RECYCLE,
    "food scraps": TEST_UPCOMING_FOODSCRAPS,
    "query_url": f"{URL_REQUEST}{TEST_LOC}",
}

TEST_NEXT_DATE_STR = "Friday, 25 March"
TEST_NEXT_TYPE_STR = ["Rubbish", "Recycling"]
TEST_NEXT_STATE = "2023-03-25"
TEST_NEXT_RUBBISH = "true"
TEST_NEXT_RECYCLE = "true"
TEST_NEXT_FOODSCRAPS = "false"
TEST_NEXT_ATTRS = {
    "location_id": TEST_LOC,
    "date": TEST_NEXT_DATE_STR,
    "rubbish": TEST_NEXT_RUBBISH,
    "recycle": TEST_NEXT_RECYCLE,
    "food scraps": TEST_NEXT_FOODSCRAPS,
    "query_url": f"{URL_REQUEST}{TEST_LOC}",
}

TEST_COORDINATOR_DATA = [
    {TEST_UPCOMING_DATE_STR: TEST_UPCOMING_TYPE_STR},
    {TEST_NEXT_DATE_STR: TEST_NEXT_TYPE_STR},
]


@freeze_time("2023-04-02")
def test_get_date_from_str_general():
    """General passing case."""

    result = get_date_from_str("Monday, 3 April")
    assert isinstance(result, date)
    assert result == date(year=2023, month=4, day=3)


@freeze_time("2023-12-30")
def test_get_date_from_str_next_year():
    """Date of next year."""

    result = get_date_from_str("Tuesday, 2 January")
    assert isinstance(result, date)
    assert result == date(year=2024, month=1, day=2)


def test_get_date_from_str_invalid_input():
    """Invalid input date string."""

    result = get_date_from_str("INVALID DATE STRING")
    assert result is None


@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_update_upcoming_success():
    """Test upcoming collection successful update."""
    _coordinator = AsyncMock()
    _coordinator.data = TEST_COORDINATOR_DATA
    upcoming = AucklandBinCollection(_coordinator, TEST_LOC, "upcoming", 0)
    await upcoming.async_update()
    assert upcoming.state == TEST_UPCOMING_STATE
    assert upcoming.extra_state_attributes == TEST_UPCOMING_ATTRS


@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_update_next_success():
    """Test next collection successful update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = TEST_COORDINATOR_DATA
    next = AucklandBinCollection(m_coordinator, TEST_LOC, "next", 1)
    await next.async_update()
    assert next.state == TEST_NEXT_STATE
    assert next.extra_state_attributes == TEST_NEXT_ATTRS


@pytest.mark.asyncio
async def test_update_upcoming_fail():
    """Test upcoming collection failed update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = None
    upcoming = AucklandBinCollection(m_coordinator, TEST_LOC, "upcoming", 0)
    await upcoming.async_update()
    assert upcoming.state is None
    assert upcoming.extra_state_attributes is None


@pytest.mark.asyncio
async def test_update_next_fail():
    """Test next collection failed update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = None
    next = AucklandBinCollection(m_coordinator, TEST_LOC, "next", 1)
    await next.async_update()
    assert next.state is None
    assert next.extra_state_attributes is None


@pytest.mark.asyncio
async def test_out_of_date_index():
    """Test getting date out of date index."""
    m_coordinator = AsyncMock()
    m_coordinator.data = [
        {"date": TEST_UPCOMING_DATE_STR, "type": TEST_UPCOMING_TYPE_STR}
    ]
    sensor = AucklandBinCollection(m_coordinator, TEST_LOC, "test_sensor", 1)
    await sensor.async_update()
    assert sensor.state is None
    assert sensor.extra_state_attributes is None


def test_name():
    """Test returning correct name."""
    m_coordinator = MagicMock()
    sensor = AucklandBinCollection(m_coordinator, TEST_LOC, "test_sensor", 0)
    assert sensor.name == "test_sensor"
