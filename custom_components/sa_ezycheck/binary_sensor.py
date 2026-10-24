"""Binary sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import entity_unique_id
from .entity import SaEzycheckEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import SaEzycheckConfigEntry
    from .coordinator import SaEzycheckCoordinator

# The coordinator already serialises updates, so entities need no extra limit.
PARALLEL_UPDATES = 0

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(key="registered", translation_key="registered"),
    BinarySensorEntityDescription(
        key="inspection_expired",
        translation_key="inspection_expired",
        device_class=BinarySensorDeviceClass.PROBLEM,
        # Reports YES for ordinary vehicles that are not subject to inspection.
        entity_registry_enabled_default=False,
    ),
    BinarySensorEntityDescription(
        key="incident",
        translation_key="incident",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="pending_suspension",
        translation_key="pending_suspension",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SaEzycheckConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the binary sensors for the vehicle."""
    coordinator = entry.runtime_data
    async_add_entities(
        SaEzycheckBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSORS
    )


class SaEzycheckBinarySensor(SaEzycheckEntity, BinarySensorEntity):
    """A binary sensor reporting one flag of the vehicle."""

    def __init__(
        self,
        coordinator: SaEzycheckCoordinator,
        device_id: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = entity_unique_id(
            coordinator.config_entry.entry_id, device_id, description.key
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the flag is set, or None when the service does not say."""
        device = self.device_data
        if device is None:
            return None
        value = device.values.get(self.entity_description.key)
        return value if isinstance(value, bool) else None
