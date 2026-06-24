"""Test for Auckland Bin Collection sensor."""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

from freezegun import freeze_time
import pytest
import pytz

from custom_components.auckland_bin_collection.sensor import (
    URL_REQUEST,
    AucklandBinCollection,
    BinCollectionCoordinator,
    POLL_HOUR,
    POLL_JITTER_SECONDS,
    RETRY_MIN_MINUTES,
    RETRY_MAX_MINUTES,
    POLL_TIMEZONE,
    _next_poll_time,
    async_get_bin_dates,
    async_setup_entry,
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
    "last_updated": None,
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
    "last_updated": None,
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
    _coordinator._last_updated = None
    upcoming = AucklandBinCollection(_coordinator, TEST_LOC, "upcoming", 0)
    assert upcoming.state == TEST_UPCOMING_STATE
    assert upcoming.extra_state_attributes == TEST_UPCOMING_ATTRS


@freeze_time("2023-01-01")
@pytest.mark.asyncio
async def test_update_next_success():
    """Test next collection successful update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = TEST_COORDINATOR_DATA
    m_coordinator._last_updated = None
    next = AucklandBinCollection(m_coordinator, TEST_LOC, "next", 1)
    assert next.state == TEST_NEXT_STATE
    assert next.extra_state_attributes == TEST_NEXT_ATTRS


@pytest.mark.asyncio
async def test_update_upcoming_fail():
    """Test upcoming collection failed update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = None
    upcoming = AucklandBinCollection(m_coordinator, TEST_LOC, "upcoming", 0)
    assert upcoming.state is None
    assert upcoming.extra_state_attributes is None


@pytest.mark.asyncio
async def test_update_next_fail():
    """Test next collection failed update."""
    m_coordinator = AsyncMock()
    m_coordinator.data = None
    next = AucklandBinCollection(m_coordinator, TEST_LOC, "next", 1)
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
    assert sensor.state is None
    assert sensor.extra_state_attributes is None


def test_name():
    """Test returning correct name."""
    m_coordinator = MagicMock()
    sensor = AucklandBinCollection(m_coordinator, TEST_LOC, "test_sensor", 0)
    assert sensor.name == "test_sensor"


# ---------------------------------------------------------------------------
# BinCollectionCoordinator tests
# ---------------------------------------------------------------------------

TZ_NZ = pytz.timezone("Pacific/Auckland")


# --- _next_poll_time --------------------------------------------------------

@freeze_time("2024-06-01 03:00:00")  # 3 AM UTC → 15:00 NZ (before 6 AM next day)
def test_next_poll_time_is_in_future():
    """_next_poll_time should always return a time in the future."""
    next_time = _next_poll_time()
    now = datetime.now(TZ_NZ)
    assert next_time > now


@freeze_time("2024-06-01 03:00:00")  # 15:00 NZ — daily target (6 AM) already past
def test_next_poll_time_schedules_tomorrow_when_past():
    """When 6 AM today has already passed, schedule for tomorrow."""
    next_time = _next_poll_time()
    now = datetime.now(TZ_NZ)
    assert next_time.date() == (now + timedelta(days=1)).date()


@freeze_time("2024-06-01 17:00:00")  # 05:00 NZ — just before 6 AM
def test_next_poll_time_schedules_today_when_not_yet_reached():
    """When 6 AM today has not yet occurred, schedule for today."""
    next_time = _next_poll_time()
    now = datetime.now(TZ_NZ)
    assert next_time.date() == now.date()


@freeze_time("2024-06-01 03:00:00")
def test_next_poll_time_within_jitter_bounds():
    """The scheduled time must be within POLL_HOUR ± POLL_JITTER_SECONDS."""
    # Run many times to exercise the random jitter
    for _ in range(50):
        next_time = _next_poll_time()
        # Convert to NZ local time for comparison
        local = next_time.astimezone(TZ_NZ)
        base = local.replace(hour=POLL_HOUR, minute=0, second=0, microsecond=0)
        diff_seconds = abs((local - base).total_seconds())
        assert diff_seconds <= POLL_JITTER_SECONDS + 1  # +1 for float rounding


# --- async_start ------------------------------------------------------------

async def test_coordinator_async_start_refreshes_and_schedules(hass):
    """async_start should perform an initial refresh and schedule the next poll."""
    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            return_value=[["dummy"]],
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ) as mock_track,
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        await coordinator.async_start()

        # A daily poll must have been scheduled
        assert mock_track.called


# --- retry on failure -------------------------------------------------------

async def test_coordinator_schedules_retry_on_fetch_failure(hass):
    """A failed initial fetch should schedule a retry via async_call_later."""
    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_call_later",
            return_value=MagicMock(),
        ) as mock_later,
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ),
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        # Simulate a failed scheduled refresh (not async_start, to skip init fetch)
        coordinator._unsub_scheduled = None
        await coordinator._do_scheduled_refresh()

        assert mock_later.called
        delay_seconds = mock_later.call_args[0][1]
        assert RETRY_MIN_MINUTES * 60 <= delay_seconds <= RETRY_MAX_MINUTES * 60


# --- success re-schedules daily poll ----------------------------------------

async def test_coordinator_reschedules_daily_poll_after_success(hass):
    """After a successful scheduled refresh, the next daily poll should be queued."""
    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            return_value=[["dummy"]],
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ) as mock_track,
        patch(
            "custom_components.auckland_bin_collection.sensor.async_call_later",
            return_value=MagicMock(),
        ) as mock_later,
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        await coordinator._do_scheduled_refresh()

        # Daily poll scheduled; retry must NOT have been called
        assert mock_track.called
        assert not mock_later.called


# --- shutdown ---------------------------------------------------------------

async def test_coordinator_shutdown_cancels_scheduled(hass):
    """async_shutdown should cancel any pending scheduled callback."""
    mock_unsub = MagicMock()
    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            return_value=[["dummy"]],
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=mock_unsub,
        ),
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        await coordinator.async_start()

        assert coordinator._unsub_scheduled is mock_unsub
        await coordinator.async_shutdown()

        mock_unsub.assert_called_once()  # The cancel callable was invoked
        assert coordinator._unsub_scheduled is None


# ---------------------------------------------------------------------------
# async_get_bin_dates tests
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html><body>
<div class="acpl-schedule-card">
  <span class="acpl-icon-with-attribute left">
    <span class="">
      Rubbish:<b>Tuesday, 12 January</b>
    </span>
  </span>
  <span class="acpl-icon-with-attribute left">
    <span class="">
      Food scraps:<b>Tuesday, 12 January</b>
    </span>
  </span>
  <span class="acpl-icon-with-attribute left">
    <span class="">
      Recycling:<b>Friday, 25 March</b>
    </span>
  </span>
</div>
</body></html>
"""


@pytest.mark.asyncio
@freeze_time("2024-06-01 03:00:00")
async def test_async_update_data_sets_last_updated(hass):
    """_async_update_data should stamp _last_updated with the current NZ time."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_HTML
    hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    coordinator = BinCollectionCoordinator(hass, TEST_LOC)
    assert coordinator._last_updated is None

    await coordinator._async_update_data()

    assert coordinator._last_updated is not None
    # Should be timezone-aware (NZ tz)
    assert coordinator._last_updated.tzinfo is not None
    # Frozen at 2024-06-01 03:00 UTC → 15:00 NZ
    assert coordinator._last_updated.strftime("%H:%M") == "15:00"


@pytest.mark.asyncio
async def test_async_get_bin_dates_success():
    """async_get_bin_dates parses a well-formed page and returns sorted data."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_HTML

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    result = await async_get_bin_dates(mock_hass, TEST_LOC)

    # Should return a list of dicts sorted by date
    assert isinstance(result, list)
    assert len(result) >= 1
    # "Food scraps" must always appear after Rubbish/Recycle so that
    # calendar UIs that only render the first 1-2 lines still show
    # the higher-priority bin types.
    assert result[0]["Tuesday, 12 January"] == ["Rubbish", "Food scraps"]


@pytest.mark.asyncio
async def test_async_get_bin_dates_food_scraps_last_even_when_listed_first():
    """When the council lists Food scraps before other types, it should still come last."""
    html = """
    <html><body>
    <div class="acpl-schedule-card">
      <span class="acpl-icon-with-attribute left">
        <span class="">
          Food scraps:<b>Tuesday, 12 January</b>
        </span>
      </span>
      <span class="acpl-icon-with-attribute left">
        <span class="">
          Rubbish:<b>Tuesday, 12 January</b>
        </span>
      </span>
      <span class="acpl-icon-with-attribute left">
        <span class="">
          Recycling:<b>Tuesday, 12 January</b>
        </span>
      </span>
    </div>
    </body></html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    result = await async_get_bin_dates(mock_hass, TEST_LOC)

    assert result[0]["Tuesday, 12 January"] == ["Rubbish", "Recycling", "Food scraps"]


@pytest.mark.asyncio
async def test_async_get_bin_dates_non_200_raises():
    """async_get_bin_dates raises UpdateFailed on a non-200 HTTP response."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    with pytest.raises(UpdateFailed, match="404"):
        await async_get_bin_dates(mock_hass, TEST_LOC)


@pytest.mark.asyncio
async def test_async_get_bin_dates_no_schedules_raises():
    """async_get_bin_dates raises UpdateFailed when no schedule cards are found."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><p>No data here</p></body></html>"

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    with pytest.raises(UpdateFailed, match="not found"):
        await async_get_bin_dates(mock_hass, TEST_LOC)


@pytest.mark.asyncio
async def test_async_get_bin_dates_empty_dates_raises():
    """async_get_bin_dates raises UpdateFailed when schedule cards have no date entries."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    empty_html = """
    <html><body>
    <div class="acpl-schedule-card">
      <span class="acpl-icon-with-attribute left">
        <!-- no inner span with class="" -->
      </span>
    </div>
    </body></html>
    """

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = empty_html

    mock_hass = MagicMock()
    mock_hass.async_add_executor_job = AsyncMock(return_value=mock_response)

    with pytest.raises(UpdateFailed, match="Cannot retrieve"):
        await async_get_bin_dates(mock_hass, TEST_LOC)


# ---------------------------------------------------------------------------
# Inner callback coverage
# ---------------------------------------------------------------------------

async def test_scheduled_refresh_callback_fires(hass):
    """The _scheduled_refresh inner callback passed to async_track_point_in_time
    should create a task that runs _do_scheduled_refresh."""
    captured_callback = None

    def capture_track(h, cb, when):
        nonlocal captured_callback
        captured_callback = cb
        return MagicMock()

    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            return_value=[["dummy"]],
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            side_effect=capture_track,
        ),
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        await coordinator.async_start()

    assert captured_callback is not None
    # Invoking the callback should schedule a task — just verify it doesn't raise
    captured_callback(datetime.now())


async def test_retry_refresh_callback_fires(hass):
    """The _retry_refresh inner callback passed to async_call_later
    should create a task that runs _do_scheduled_refresh."""
    captured_callback = None

    def capture_later(h, delay, cb):
        nonlocal captured_callback
        captured_callback = cb
        return MagicMock()

    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_get_bin_dates",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_call_later",
            side_effect=capture_later,
        ),
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ),
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        coordinator._unsub_scheduled = None
        await coordinator._do_scheduled_refresh()

    assert captured_callback is not None
    captured_callback(datetime.now())


# ---------------------------------------------------------------------------
# _do_scheduled_refresh bare-except branch (line 182)
# ---------------------------------------------------------------------------

async def test_do_scheduled_refresh_exception_schedules_retry(hass):
    """An unexpected exception in async_refresh triggers _schedule_retry.

    DataUpdateCoordinator.async_refresh() catches exceptions from
    _async_update_data internally and never re-raises them, so patching
    async_get_bin_dates is NOT enough to hit the bare `except` on line 182.
    We must patch async_refresh itself to raise.
    """
    with (
        patch(
            "custom_components.auckland_bin_collection.sensor.async_call_later",
            return_value=MagicMock(),
        ) as mock_later,
        patch(
            "custom_components.auckland_bin_collection.sensor.async_track_point_in_time",
            return_value=MagicMock(),
        ),
    ):
        coordinator = BinCollectionCoordinator(hass, TEST_LOC)
        # Patch the coordinator's own async_refresh so it raises rather than swallowing
        coordinator.async_refresh = AsyncMock(side_effect=RuntimeError("hard failure"))
        await coordinator._do_scheduled_refresh()

        assert mock_later.called


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------

async def test_async_setup_entry(hass):
    """async_setup_entry creates BinCollectionCoordinator and adds two entities."""
    mock_entry = MagicMock()
    mock_entry.data = {"location_id": TEST_LOC}
    mock_entry.entry_id = "test_entry_id"
    hass.data.setdefault("auckland_bin_collection", {})

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

    assert len(added_entities) == 2
    assert all(isinstance(e, AucklandBinCollection) for e in added_entities)
