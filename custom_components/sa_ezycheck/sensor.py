"""Sensor platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import entity_unique_id
from .entity import SaEzycheckEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from typing import Any

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from . import SaEzycheckConfigEntry
    from .api import DeviceData
    from .coordinator import SaEzycheckCoordinator

# The coordinator already serialises updates, so entities need no extra limit.
PARALLEL_UPDATES = 0


def _days_until_expiry(device: DeviceData) -> int | None:
    """Return the whole days until the registration expires (negative if past)."""
    expiry = device.values.get("expiry_date")
    if not isinstance(expiry, date):
        return None
    return (expiry - dt_util.now().date()).days


@dataclass(frozen=True, kw_only=True)
class SaEzycheckSensorDescription(SensorEntityDescription):
    """Describes a sensor, read by key or computed from the device."""

    value_fn: Callable[[DeviceData], StateType | date] | None = None
    # Recompute at the start of each day, since the value depends on today's date.
    refresh_daily: bool = False
    # Expose the vehicle's free-text details (conditions, GVM, ...) as attributes.
    include_attributes: bool = False


SENSORS: tuple[SaEzycheckSensorDescription, ...] = (
    SaEzycheckSensorDescription(
        key="expiry_date",
        translation_key="expiry_date",
        device_class=SensorDeviceClass.DATE,
        include_attributes=True,
    ),
    SaEzycheckSensorDescription(
        key="days_until_expiry",
        translation_key="days_until_expiry",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=_days_until_expiry,
        refresh_daily=True,
    ),
    SaEzycheckSensorDescription(
        key="inspection_due_date",
        translation_key="inspection_due_date",
        device_class=SensorDeviceClass.DATE,
    ),
    SaEzycheckSensorDescription(key="make", translation_key="make"),
    SaEzycheckSensorDescription(key="body_type", translation_key="body_type"),
    SaEzycheckSensorDescription(key="primary_colour", translation_key="primary_colour"),
    SaEzycheckSensorDescription(key="ctp_insurer", translation_key="ctp_insurer"),
    SaEzycheckSensorDescription(
        key="plate_type",
        translation_key="plate_type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SaEzycheckSensorDescription(
        key="premium_class",
        translation_key="premium_class",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SaEzycheckSensorDescription(
        key="masked_vin",
        translation_key="masked_vin",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SaEzycheckConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the sensors for the vehicle."""
    coordinator = entry.runtime_data
    async_add_entities(
        SaEzycheckSensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in SENSORS
    )


class SaEzycheckSensor(SaEzycheckEntity, SensorEntity):
    """A sensor reporting one value of the vehicle."""

    def __init__(
        self,
        coordinator: SaEzycheckCoordinator,
        device_id: str,
        description: SaEzycheckSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._description = description
        self._attr_unique_id = entity_unique_id(
            coordinator.config_entry.entry_id, device_id, description.key
        )

    async def async_added_to_hass(self) -> None:
        """Schedule the daily refresh for values that depend on today's date."""
        await super().async_added_to_hass()
        if self._description.refresh_daily:
            self.async_on_remove(
                async_track_time_change(
                    self.hass, self._async_new_day, hour=0, minute=0, second=1
                )
            )

    @callback
    def _async_new_day(self, _now: datetime) -> None:
        """Recompute the state when the date changes."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> StateType | date:
        """Return the current value."""
        device = self.device_data
        if device is None:
            return None
        if self._description.value_fn is not None:
            return self._description.value_fn(device)
        return device.values.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the vehicle's free-text details when this sensor carries them."""
        device = self.device_data
        if device is None or not self._description.include_attributes:
            return None
        return dict(device.attributes) or None
