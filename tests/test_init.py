# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for __init__.py: entry setup, unload and retry behaviour."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import device_registry as dr

from custom_components.sa_ezycheck.api import SaEzycheckConnectionError
from custom_components.sa_ezycheck.binary_sensor import (
    BINARY_SENSORS,
    SaEzycheckBinarySensor,
)
from custom_components.sa_ezycheck.const import device_identifier
from custom_components.sa_ezycheck.sensor import SENSORS, SaEzycheckSensor

from .conftest import FETCH_TARGET, FIRST_DEVICE_ID, PLATE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_creates_the_vehicle_device_and_unload_unloads_the_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    device = dr.async_get(hass).async_get_device_by_identifier(
        device_identifier(init_integration.entry_id, FIRST_DEVICE_ID),
        init_integration.entry_id,
    )
    assert device is not None
    assert device.name == PLATE
    assert device.manufacturer == "FORD"
    assert device.model == "SEDAN"

    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_the_first_refresh_fails(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch(FETCH_TARGET, side_effect=SaEzycheckConnectionError("down")):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_entities_become_unavailable_when_updates_fail(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    mock_fetch.side_effect = SaEzycheckConnectionError("down")

    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(f"sensor.{PLATE.lower()}_make")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_entities_have_no_value_when_the_vehicle_is_no_longer_reported(
    init_integration: MockConfigEntry,
) -> None:
    coordinator = init_integration.runtime_data
    sensor = SaEzycheckSensor(coordinator, FIRST_DEVICE_ID, SENSORS[0])
    binary_sensor = SaEzycheckBinarySensor(
        coordinator, FIRST_DEVICE_ID, BINARY_SENSORS[0]
    )
    assert sensor.available
    assert sensor.native_value is not None
    assert sensor.extra_state_attributes is None
    assert binary_sensor.is_on is True

    coordinator.data = replace(coordinator.data, devices={})

    assert not sensor.available
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None
    assert not binary_sensor.available
    assert binary_sensor.is_on is None
