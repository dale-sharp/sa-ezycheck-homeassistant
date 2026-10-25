# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Diagnostics download with the plate, VIN digits and vehicle name redacted."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_PLATE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import SaEzycheckConfigEntry

# The plate identifies the vehicle and the VIN digits identify it further: diagnostics
# are attached to public issue reports.
TO_REDACT = {CONF_PLATE, "name", "masked_vin"}
SAMPLE_DEVICES = 10


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: SaEzycheckConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    devices = coordinator.data.devices if coordinator.data else {}
    return {
        "entry": async_redact_data(
            {"title": entry.title, **entry.data}, {*TO_REDACT, "title"}
        ),
        "options": dict(entry.options),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "data_summary": {
            "device_count": len(devices),
            "sample_devices": {
                device_id: async_redact_data(
                    {
                        "name": device.name,
                        "values": {
                            key: value.isoformat() if isinstance(value, date) else value
                            for key, value in device.values.items()
                        },
                        "attributes": dict(device.attributes),
                    },
                    TO_REDACT,
                )
                for device_id, device in list(devices.items())[:SAMPLE_DEVICES]
            },
        },
    }
