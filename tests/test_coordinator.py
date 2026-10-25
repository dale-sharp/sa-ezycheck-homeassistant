# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for coordinator.py: parsing, update interval and the repair issue."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_ezycheck.api import SaEzycheckConnectionError
from custom_components.sa_ezycheck.const import (
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    ISSUE_PERSISTENT_FETCH_FAILURE,
    OPTION_SCAN_INTERVAL_MINUTES,
    PERSISTENT_FETCH_FAILURE_THRESHOLD,
)

from .conftest import FIRST_DEVICE_ID, INVALID_PLATE_RESPONSE, PLATE

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from homeassistant.core import HomeAssistant


async def test_refresh_returns_parsed_data(
    init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    data = init_integration.runtime_data.data

    assert FIRST_DEVICE_ID in data.devices
    assert data.devices[FIRST_DEVICE_ID].values["expiry_date"] == date(2026, 11, 2)
    mock_fetch.assert_awaited_with(PLATE)


async def test_update_interval_comes_from_options(
    hass: HomeAssistant, mock_fetch: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=mock_config_entry.title,
        unique_id=mock_config_entry.unique_id,
        data=dict(mock_config_entry.data),
        options={OPTION_SCAN_INTERVAL_MINUTES: 90},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.update_interval == timedelta(minutes=90)
    assert entry.runtime_data.update_interval != timedelta(
        minutes=DEFAULT_SCAN_INTERVAL_MINUTES
    )


async def test_repair_issue_is_raised_after_consecutive_failures_and_cleared(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    coordinator = init_integration.runtime_data
    issue_id = f"{ISSUE_PERSISTENT_FETCH_FAILURE}_{init_integration.entry_id}"
    registry = ir.async_get(hass)
    mock_fetch.side_effect = SaEzycheckConnectionError("down")

    for _ in range(PERSISTENT_FETCH_FAILURE_THRESHOLD - 1):
        await coordinator.async_refresh()
    assert registry.async_get_issue(DOMAIN, issue_id) is None

    await coordinator.async_refresh()
    assert registry.async_get_issue(DOMAIN, issue_id) is not None

    mock_fetch.side_effect = None
    await coordinator.async_refresh()
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_update_fails_with_a_translated_error_when_the_plate_is_refused(
    init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    coordinator = init_integration.runtime_data
    mock_fetch.return_value = INVALID_PLATE_RESPONSE

    await coordinator.async_refresh()

    assert not coordinator.last_update_success
    assert coordinator.last_exception.translation_key == "invalid_plate"
    assert coordinator.last_exception.translation_placeholders == {"plate": PLATE}
