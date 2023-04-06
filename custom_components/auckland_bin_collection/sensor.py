"""Auckland Bin Collection sensor component"""

import logging
import requests
import pytz
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import datetime, timedelta
from typing import Any
from bs4 import BeautifulSoup
from .const import CONF_LOCATION_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

KEY_DATE = "date"
KEY_TYPE = "type"
URL_REQUEST = "https://www.aucklandcouncil.govt.nz/rubbish-recycling/rubbish-recycling-collections/Pages/collection-day-detail.aspx?an="


def get_date_from_str(date_str: str) -> datetime.date:
    """Convert a date string to date object"""

    try:
        input_date = datetime.strptime(date_str, "%A %d %B")
    except ValueError as e:
        _LOGGER.error("Invalid input date string.")
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

    url = f"{URL_REQUEST}{location_id}"
    response = await hass.async_add_executor_job(requests.get, url)

    soup = BeautifulSoup(response.text, "html.parser")
    household = soup.find_all("div", {"id": lambda x: x and "HouseholdBlock" in x})

    result = []
    # We can assume only one Household Block
    for collect_date in household[0].find_all("span", {"class": "m-r-1"}):
        collect_types = []
        for sibling in collect_date.find_next_siblings():
            collect_type = sibling.find("span", {"class": "sr-only"})
            if collect_type:
                collect_types.append(collect_type.text)
        result.append({KEY_DATE: collect_date.text, KEY_TYPE: collect_types})

    return result


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

        return get_date_from_str(
            self.coordinator.data[self._date_index][KEY_DATE]
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        try:
            data = self.coordinator.data[self._date_index]
        except IndexError:
            _LOGGER.debug(
                "coordinator.data with _date_index: %d not ready yet", self._date_index
            )
            return None

        return {
            "location_id": self._location_id,
            "date": data[KEY_DATE],
            "rubbish": "true" if "Rubbish" in data[KEY_TYPE] else "false",
            "recycle": "true" if "Recycle" in data[KEY_TYPE] else "false",
            "query_url": f"{URL_REQUEST}{self._location_id}",
        }

    async def async_update(self):
        """Handle data update."""
        await self.coordinator.async_request_refresh()
