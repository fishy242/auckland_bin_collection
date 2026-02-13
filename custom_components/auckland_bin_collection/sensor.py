"""Auckland Bin Collection sensor component"""

from datetime import datetime, timedelta
import logging
from typing import Any
from functools import partial

from bs4 import BeautifulSoup
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import pytz
import requests

from .const import CONF_LOCATION_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

KEY_DATE = "date"
KEY_TYPE = "type"
URL_REQUEST = "https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days/"
UA_HEADER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"

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
    agent_header = {"User-Agent": UA_HEADER, "Accept-Encoding":"gzip, deflate, br, zstd", "Accept-Language": "en-NZ,en;q=0.9"}
    req_func = partial(requests.get, url, headers=agent_header)
    response = await hass.async_add_executor_job(req_func)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    schedules = soup.find_all("div", {"class": "acpl-schedule-card"})

    if not schedules:
        raise ValueError("Data with location ID not found")

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
        raise ValueError("Cannot retrieve bin dates")

    data_dict = {}
    for collect_date, collect_type in extracted_data:
        if collect_date not in data_dict:
            data_dict[collect_date] = []
        data_dict[collect_date].append(collect_type)

    sorted_date = sorted(data_dict.keys(), key=get_date_from_str)
    sorted_data = [{collect_date: data_dict[collect_date]} for collect_date in sorted_date]

    return sorted_data


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Auckland Bin Collection entities from a config_entry."""

    location_id = entry.data[CONF_LOCATION_ID]

    coordinator = DataUpdateCoordinator(
        hass=hass,
        logger=_LOGGER,
        update_method=lambda: async_get_bin_dates(hass, location_id),
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )

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
