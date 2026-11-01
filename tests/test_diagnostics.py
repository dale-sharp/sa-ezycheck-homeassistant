# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for diagnostics.py: structure, serialisability and redaction."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_ezycheck.const import DOMAIN
from custom_components.sa_ezycheck.diagnostics import (
    SAMPLE_DEVICES,
    async_get_config_entry_diagnostics,
)

from .conftest import FIRST_DEVICE_ID, INVALID_PLATE_RESPONSE, PLATE

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from homeassistant.core import HomeAssistant


async def test_diagnostics_has_the_expected_structure(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert result["options"] == dict(init_integration.options)
    assert result["coordinator"]["last_update_success"] is True
    assert result["coordinator"]["last_exception"] is None
    assert result["coordinator"]["update_interval_seconds"] > 0
    summary = result["data_summary"]
    assert summary["device_count"] >= 1
    assert FIRST_DEVICE_ID in summary["sample_devices"]
    assert len(summary["sample_devices"]) <= SAMPLE_DEVICES
    values = summary["sample_devices"][FIRST_DEVICE_ID]["values"]
    assert values["expiry_date"] == "2026-11-02"
    assert values["make"] == "FORD"


async def test_diagnostics_redacts_the_plate_and_vin(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert PLATE not in json.dumps(result)
    assert "0000" not in json.dumps(result)
    device = result["data_summary"]["sample_devices"][FIRST_DEVICE_ID]
    assert device["name"] == "**REDACTED**"
    assert device["values"]["masked_vin"] == "**REDACTED**"
    assert result["entry"] == {"title": "**REDACTED**", "plate": "**REDACTED**"}


async def test_diagnostics_redacts_the_plate_from_the_last_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    # The error shown to the user names the plate, so it must not reach the download.
    mock_fetch.return_value = INVALID_PLATE_RESPONSE
    await init_integration.runtime_data.async_refresh()

    result = await async_get_config_entry_diagnostics(hass, init_integration)

    last_exception = result["coordinator"]["last_exception"]
    assert PLATE not in last_exception
    assert "**REDACTED**" in last_exception
    assert PLATE not in json.dumps(result)


async def test_diagnostics_output_is_json_serialisable(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert json.loads(json.dumps(result)) == result


async def test_diagnostics_handles_a_coordinator_without_data(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.runtime_data = MagicMock(
        data=None,
        last_update_success=False,
        last_exception=RuntimeError("boom"),
        update_interval=None,
    )

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["coordinator"]["last_exception"] == "boom"
    assert result["coordinator"]["update_interval_seconds"] is None
    assert result["data_summary"] == {"device_count": 0, "sample_devices": {}}
