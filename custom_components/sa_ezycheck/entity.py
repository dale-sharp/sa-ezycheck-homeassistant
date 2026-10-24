"""Base entity for the integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import device_identifier
from .coordinator import SaEzycheckCoordinator

if TYPE_CHECKING:
    from .api import DeviceData


class SaEzycheckEntity(CoordinatorEntity[SaEzycheckCoordinator]):
    """Base class: coordinator wiring and device registration for every entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SaEzycheckCoordinator, device_id: str) -> None:
        """Initialise the entity for one device of the coordinator's data."""
        super().__init__(coordinator)
        self._device_id = device_id
        device = coordinator.data.devices[device_id]
        self._attr_device_info = DeviceInfo(
            identifiers={
                device_identifier(coordinator.config_entry.entry_id, device_id)
            },
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
        )

    @property
    def device_data(self) -> DeviceData | None:
        """Return this entity's device from the latest data, if still reported."""
        return self.coordinator.data.devices.get(self._device_id)

    @property
    def available(self) -> bool:
        """Return whether the device is still reported by the API."""
        return super().available and self.device_data is not None
