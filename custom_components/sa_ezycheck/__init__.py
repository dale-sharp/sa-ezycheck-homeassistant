"""The integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .coordinator import SaEzycheckCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
]

# Typed config entry alias; runtime_data holds the coordinator.
type SaEzycheckConfigEntry = ConfigEntry[SaEzycheckCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SaEzycheckConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    coordinator = SaEzycheckCoordinator(hass, entry)
    # Raises ConfigEntryNotReady on failure, so Home Assistant retries the setup.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SaEzycheckConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
