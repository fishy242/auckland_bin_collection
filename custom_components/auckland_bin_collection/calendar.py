"""Calendar platform for the Auckland Bin Collection integration."""

from datetime import datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import pytz
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LOCATION_ID, DOMAIN
from .sensor import BinCollectionCoordinator, get_date_from_str

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the calendar platform."""
    location_id = entry.data[CONF_LOCATION_ID]

    # Use the shared coordinator if it was already created by the sensor platform
    if entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id]
    else:
        coordinator = BinCollectionCoordinator(hass, location_id)
        await coordinator.async_start()
        hass.data[DOMAIN][entry.entry_id] = coordinator

    async_add_entities([AucklandBinCollectionCalendar(coordinator, location_id)])


class AucklandBinCollectionCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for Auckland Bin Collections."""

    _attr_has_entity_name = True
    _attr_name = "Auckland Bin Collection"

    def __init__(self, coordinator: BinCollectionCoordinator, location_id: str) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._location_id = location_id
        # Unique ID combining domain, location, and platform
        self._attr_unique_id = f"{DOMAIN}_{location_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming calendar event."""
        if not self.coordinator.data or len(self.coordinator.data) == 0:
            return None

        # Data structure: [{ "Wednesday, 14 April": ["Rubbish", "Recycling"] }, ...]
        first_collection = self.coordinator.data[0]
        date_str = list(first_collection.keys())[0]
        bin_types = first_collection[date_str]

        if not bin_types:
            return None

        date_obj = get_date_from_str(date_str)
        if not date_obj:
            return None

        # Return just the first bin type from the earliest day as the immediate "next" event property state
        return CalendarEvent(
            summary=bin_types[0],
            start=date_obj,
            end=date_obj + timedelta(days=1),
            description="Auckland Council Bin Collection",
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events: list[CalendarEvent] = []

        if not self.coordinator.data:
            return events

        for collection in self.coordinator.data:
            date_str = list(collection.keys())[0]
            bin_types = collection[date_str]
            date_obj = get_date_from_str(date_str)

            if not date_obj:
                continue

            # start_date and end_date are timezone aware datetime objects.
            # date_obj is a datetime.date object. We convert it to datetime at midnight NZ time.
            nz_tz = pytz.timezone("Pacific/Auckland")
            event_start = nz_tz.localize(datetime.combine(date_obj, datetime.min.time()))

            if start_date <= event_start < end_date:
                for bin_type in bin_types:
                    events.append(
                        CalendarEvent(
                            summary=bin_type,
                            start=date_obj,
                            end=date_obj + timedelta(days=1),
                            description="Auckland Council Bin Collection",
                        )
                    )

        return events
