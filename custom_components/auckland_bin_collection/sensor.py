"""Auckland Bin Collection sensor component"""

from datetime import datetime, timedelta
import logging
import random
from typing import Any
from functools import partial

from bs4 import BeautifulSoup
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_point_in_time
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import pytz
import requests

from .const import CONF_LOCATION_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

KEY_DATE = "date"
KEY_TYPE = "type"
URL_REQUEST = "https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days/"
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"

# Scheduling configuration
POLL_TIMEZONE = pytz.timezone("Pacific/Auckland")
POLL_HOUR = 6          # Daily poll target: 6:00 AM NZ time
POLL_JITTER_MINUTES = 30   # ± random variation around the target time (minutes)
RETRY_MIN_MINUTES = 30     # Minimum retry delay after a failed poll (minutes)
RETRY_MAX_MINUTES = 90     # Maximum retry delay after a failed poll (minutes)


def get_date_from_str(date_str: str) -> datetime.date:
    """Convert a date string to date object"""

    try:
        input_date = datetime.strptime(date_str, "%A, %d %B")
    except ValueError:
        _LOGGER.error("Invalid input date string")
        return None

    timezone = pytz.timezone("Pacific/Auckland")
    current_date = datetime.now()

    if (input_date.month == 1) and (current_date.month == 12):
        input_date = input_date.replace(year=current_date.year + 1)
    else:
        input_date = input_date.replace(year=current_date.year)

    return timezone.localize(input_date).date()


async def async_get_bin_dates(hass: HomeAssistant, location_id: str):
    """Async method to get data from Auckland Council webpage."""

    url = f"{URL_REQUEST}{location_id}.html"
    agent_header = {"User-Agent": UA_HEADER, "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "en-NZ,en;q=0.9"}
    req_func = partial(requests.get, url, headers=agent_header)
    response = await hass.async_add_executor_job(req_func)

    if response.status_code != 200:
        raise UpdateFailed(f"Failed to fetch page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    schedules = soup.find_all("div", {"class": "acpl-schedule-card"})

    if not schedules:
        raise UpdateFailed("Data with location ID not found")

    extracted_data = []
    # We can assume first block is the household schedule
    for date_block in schedules[0].find_all("span", {"class": "acpl-icon-with-attribute left"}):
        date_field = date_block.find("span", {"class", ""})
        if date_field:
            collect_type = date_field.contents[0].strip().rstrip(':')
            collect_date = date_field.find("b").string
            if collect_date and collect_type:
                extracted_data.append((collect_date.text, collect_type))

    if not extracted_data:
        raise UpdateFailed("Cannot retrieve bin dates")

    data_dict = {}
    for collect_date, collect_type in extracted_data:
        if collect_date not in data_dict:
            data_dict[collect_date] = []
        data_dict[collect_date].append(collect_type)

    sorted_date = sorted(data_dict.keys(), key=get_date_from_str)
    sorted_data = [{collect_date: data_dict[collect_date]} for collect_date in sorted_date]

    return sorted_data


def _next_poll_time() -> datetime:
    """Calculate the next daily poll time: POLL_HOUR NZ time ± POLL_JITTER_MINUTES."""
    now = datetime.now(POLL_TIMEZONE)
    jitter = random.randint(-POLL_JITTER_MINUTES, POLL_JITTER_MINUTES)
    target = now.replace(hour=POLL_HOUR, minute=0, second=0, microsecond=0) + timedelta(minutes=jitter)

    # If the target time today has already passed, schedule for tomorrow
    if target <= now:
        target += timedelta(days=1)

    _LOGGER.debug(
        "Next scheduled poll at %s (jitter: %+d min)",
        target.strftime("%Y-%m-%d %H:%M:%S %Z"),
        jitter,
    )
    return target


class BinCollectionCoordinator(DataUpdateCoordinator):
    """Custom coordinator that polls once daily at a fixed NZ time with random jitter.

    On failure, it schedules a retry after a random delay instead of waiting
    until the next daily window, to recover data without hammering the server.
    """

    def __init__(self, hass: HomeAssistant, location_id: str) -> None:
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            # No fixed update_interval — we manage scheduling ourselves
            update_interval=None,
        )
        self._location_id = location_id
        self._unsub_scheduled: callback | None = None

    async def async_start(self) -> None:
        """Start the coordinator: fetch immediately if no data, then schedule daily polls."""
        _LOGGER.debug("BinCollectionCoordinator starting")
        await self.async_refresh()  # Initial fetch on startup
        self._schedule_next_poll()

    def _schedule_next_poll(self) -> None:
        """Schedule the next daily poll at the target time with jitter."""
        self._cancel_scheduled()
        next_time = _next_poll_time()

        @callback
        def _scheduled_refresh(_now: datetime) -> None:
            self.hass.async_create_task(self._do_scheduled_refresh())

        self._unsub_scheduled = async_track_point_in_time(
            self.hass, _scheduled_refresh, next_time
        )

    def _schedule_retry(self) -> None:
        """Schedule a retry after a random delay following a failed poll."""
        self._cancel_scheduled()
        delay_minutes = random.randint(RETRY_MIN_MINUTES, RETRY_MAX_MINUTES)
        delay_seconds = delay_minutes * 60

        _LOGGER.warning(
            "Last poll failed — retrying in %d minutes", delay_minutes
        )

        @callback
        def _retry_refresh(_now: datetime) -> None:
            self.hass.async_create_task(self._do_scheduled_refresh())

        self._unsub_scheduled = async_call_later(
            self.hass, delay_seconds, _retry_refresh
        )

    async def _do_scheduled_refresh(self) -> None:
        """Perform a scheduled refresh, then schedule the next poll or a retry."""
        try:
            await self.async_refresh()
            if self.last_update_success:
                _LOGGER.debug("Scheduled poll succeeded — scheduling next daily poll")
                self._schedule_next_poll()
            else:
                self._schedule_retry()
        except Exception:  # noqa: BLE001
            self._schedule_retry()

    def _cancel_scheduled(self) -> None:
        """Cancel any pending scheduled callback."""
        if self._unsub_scheduled is not None:
            self._unsub_scheduled()
            self._unsub_scheduled = None

    async def _async_update_data(self):
        """Fetch data from the Auckland Council website."""
        return await async_get_bin_dates(self.hass, self._location_id)

    async def async_shutdown(self) -> None:
        """Cancel scheduled polls on shutdown."""
        self._cancel_scheduled()
        await super().async_shutdown()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Auckland Bin Collection entities from a config_entry."""

    location_id = entry.data[CONF_LOCATION_ID]

    coordinator = BinCollectionCoordinator(hass, location_id)
    await coordinator.async_start()

    async_add_entities(
        [
            AucklandBinCollection(
                coordinator, location_id, "Auckland Bin Collection Upcoming", 0
            ),
            AucklandBinCollection(
                coordinator, location_id, "Auckland Bin Collection Next", 1
            ),
        ]
    )


class AucklandBinCollection(SensorEntity):
    """AucklandBinCollection class."""

    def __init__(self, coordinator, location_id, name, date_index) -> None:
        self.coordinator = coordinator
        self._location_id = location_id
        self._name = name
        self._date_index = date_index

    @property
    def name(self):
        return self._name

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        if not self.coordinator.data:
            return None

        try:
            data = self.coordinator.data[self._date_index]
        except IndexError:
            _LOGGER.info(
                "coordinator.data with _date_index: %d not ready yet", self._date_index
            )
            return None

        return get_date_from_str(list(data.keys())[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        try:
            data = self.coordinator.data[self._date_index]
        except IndexError:
            _LOGGER.info(
                "coordinator.data with _date_index: %d not ready yet", self._date_index
            )
            return None

        date = list(data.keys())[0]
        return {
            "location_id": self._location_id,
            "date": date,
            "rubbish": "true" if "Rubbish" in data[date] else "false",
            "recycle": "true" if "Recycling" in data[date] else "false",
            "food scraps": "true" if "Food scraps" in data[date] else "false",
            "query_url": f"{URL_REQUEST}{self._location_id}",
        }

    @property
    def device_class(self) -> SensorDeviceClass:
        return SensorDeviceClass.DATE

    async def async_update(self):
        """Handle data update."""
        await self.coordinator.async_request_refresh()
