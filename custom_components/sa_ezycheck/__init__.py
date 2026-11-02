# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SA EzyCheck: South Australian vehicle registration expiry and status by plate."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, persistent_fetch_failure_issue_id
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
    # A failed fetch raises ConfigEntryNotReady, so Home Assistant retries the setup. A
    # plate the service refuses raises ConfigEntryError instead, which stops it.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SaEzycheckConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: SaEzycheckConfigEntry) -> None:
    """Clear the repair issue of a removed config entry, so it cannot linger."""
    ir.async_delete_issue(
        hass, DOMAIN, persistent_fetch_failure_issue_id(entry.entry_id)
    )
