"""Calendar platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityDescription,
    CalendarEvent,
)
from homeassistant.util import dt as dt_util

from .const import entity_unique_id
from .entity import SaEzycheckEntity

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SaEzycheckConfigEntry
    from .coordinator import SaEzycheckCoordinator

# The coordinator already serialises updates, so entities need no extra limit.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SaEzycheckCalendarDescription(CalendarEntityDescription):
    """Describes a calendar with one all-day event on a date the service reports."""

    # Key of the date in DeviceData.values.
    date_key: str
    # Event title; "{plate}" is replaced with the vehicle's plate.
    summary: str


CALENDARS: tuple[SaEzycheckCalendarDescription, ...] = (
    SaEzycheckCalendarDescription(
        key="registration",
        translation_key="registration",
        date_key="expiry_date",
        summary="{plate} registration expires",
    ),
    SaEzycheckCalendarDescription(
        key="inspection",
        translation_key="inspection",
        date_key="inspection_due_date",
        summary="{plate} inspection due",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SaEzycheckConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the calendars for the vehicle."""
    coordinator = entry.runtime_data
    async_add_entities(
        SaEzycheckCalendar(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in CALENDARS
    )


class SaEzycheckCalendar(SaEzycheckEntity, CalendarEntity):
    """A calendar holding the all-day event for one date of the vehicle."""

    def __init__(
        self,
        coordinator: SaEzycheckCoordinator,
        device_id: str,
        description: SaEzycheckCalendarDescription,
    ) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._description = description
        self._attr_unique_id = entity_unique_id(
            coordinator.config_entry.entry_id, device_id, description.key
        )

    def _vehicle_event(self) -> CalendarEvent | None:
        """Return the event for the reported date, or None when there is no date."""
        device = self.device_data
        if device is None:
            return None
        due = device.values.get(self._description.date_key)
        if not isinstance(due, date):
            return None
        return CalendarEvent(
            start=due,
            end=due + timedelta(days=1),
            summary=self._description.summary.format(plate=device.name),
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the event while it is ongoing or still ahead, and None once past."""
        event = self._vehicle_event()
        if event is None or event.end <= dt_util.now().date():
            return None
        return event

    async def async_get_events(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return the event if it overlaps the requested range."""
        event = self._vehicle_event()
        if (
            event is None
            or event.start >= dt_util.as_local(end_date).date()
            or event.end <= dt_util.as_local(start_date).date()
        ):
            return []
        return [event]
