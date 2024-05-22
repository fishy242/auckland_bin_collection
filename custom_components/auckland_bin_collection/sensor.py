"""Auckland Bin Collection sensor component"""

from datetime import datetime, timedelta
import logging
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import pytz
import requests

#from .const import CONF_LOCATION_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

KEY_DATE = "date"
KEY_TYPE = "type"
URL_REQUEST = "https://www.aucklandcouncil.govt.nz/rubbish-recycling/rubbish-recycling-collections/Pages/collection-day-detail.aspx?an="


def get_date_from_str(date_str: str) -> datetime.date:
    """Convert a date string to date object"""

    try:
        input_date = datetime.strptime(date_str, "%A %d %B")
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

    url = f"{URL_REQUEST}{location_id}"
    response = await hass.async_add_executor_job(requests.get, url)

#def sensor_test():
#    location_id = "12342731560"
    url = f"{URL_REQUEST}{location_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    household = soup.find_all("div", {"id": lambda x: x and "HouseholdBlock2" in x})

    if not household:
        raise ValueError("Data with location ID not found")

    result = []
    # We can assume only one Household Block
    for date_block in household[0].find_all("h5", {"class": "collectionDayDate"}):
        collect_type = date_block.find("span", {"class": "sr-only"})
        collect_date = date_block.find("strong")
        if collect_date and collect_type:
            result.append({KEY_DATE: collect_date.text, KEY_TYPE: collect_type.text})

    if not result:
        raise ValueError("Cannot retrieve bin dates")

    print(f"return: {result}")
    return result

#if __name__ == "__main__":
 #   sensor_test()

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
            _LOGGER.warn(
                "coordinator.data with _date_index: %d not ready yet", self._date_index
            )
            return None

        return get_date_from_str(data[KEY_DATE])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        try:
            data = self.coordinator.data[self._date_index]
        except IndexError:
            _LOGGER.warn(
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
