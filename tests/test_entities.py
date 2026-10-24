"""Tests for the sensor and binary sensor platforms: states, attributes and the daily refresh."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.sa_ezycheck.const import DOMAIN, entity_unique_id

from .conftest import FIRST_DEVICE_ID, PLATE, record_xml, response_xml

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from pytest_homeassistant_custom_component.common import MockConfigEntry


def _entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, entity_unique_id(entry.entry_id, FIRST_DEVICE_ID, key)
    )
    assert entity_id is not None
    return entity_id


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None
    return state


@pytest.mark.parametrize(
    ("platform", "key", "state"),
    [
        ("sensor", "expiry_date", "2026-11-02"),
        ("sensor", "days_until_expiry", "8"),
        ("sensor", "inspection_due_date", STATE_UNKNOWN),
        ("sensor", "make", "FORD"),
        ("sensor", "body_type", "SEDAN"),
        ("sensor", "primary_colour", "ORANGE"),
        ("sensor", "ctp_insurer", "NRMA"),
        ("sensor", "plate_type", "ALPHANUMERIC"),
        ("sensor", "premium_class", "1 - CARS (SEDAN, STN WAGON, ETC)"),
        ("binary_sensor", "registered", STATE_ON),
        ("binary_sensor", "incident", STATE_OFF),
        ("binary_sensor", "pending_suspension", STATE_OFF),
    ],
)
async def test_entity_states(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    platform: str,
    key: str,
    state: str,
) -> None:
    entity_id = _entity_id(hass, init_integration, platform, key)

    assert entity_id.startswith(f"{platform}.{PLATE.lower()}_")
    assert _state(hass, entity_id).state == state


@pytest.mark.parametrize(
    ("platform", "key"),
    [("sensor", "masked_vin"), ("binary_sensor", "inspection_expired")],
)
async def test_noisy_entities_are_disabled_by_default(
    hass: HomeAssistant, init_integration: MockConfigEntry, platform: str, key: str
) -> None:
    entity_id = _entity_id(hass, init_integration, platform, key)

    registry_entry = er.async_get(hass).async_get(entity_id)
    assert registry_entry is not None
    assert registry_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None


async def test_expiry_sensor_exposes_filled_in_details_as_attributes(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    entity_id = _entity_id(hass, init_integration, "sensor", "expiry_date")
    assert "vehicle_conditions" not in _state(hass, entity_id).attributes

    mock_fetch.return_value = response_xml(
        record_xml(vehicleConditions="LIGHT TRAILER")
    )
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert _state(hass, entity_id).attributes["vehicle_conditions"] == "LIGHT TRAILER"


async def test_unregistered_vehicle_has_no_expiry(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    mock_fetch.return_value = response_xml(
        record_xml(expiryDate="UNREGISTERED", incidentInd=None)
    )
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    for platform, key, state in (
        ("sensor", "expiry_date", STATE_UNKNOWN),
        ("sensor", "days_until_expiry", STATE_UNKNOWN),
        ("binary_sensor", "registered", STATE_OFF),
        ("binary_sensor", "incident", STATE_UNKNOWN),
    ):
        entity_id = _entity_id(hass, init_integration, platform, key)
        assert _state(hass, entity_id).state == state, key


async def test_days_until_expiry_updates_at_midnight_without_a_new_poll(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_fetch: AsyncMock,
    today: FrozenDateTimeFactory,
) -> None:
    entity_id = _entity_id(hass, init_integration, "sensor", "days_until_expiry")
    # One minute before local midnight (the test time zone is UTC-7), right after a poll.
    today.move_to("2026-10-26 06:59:00+00:00")
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, entity_id).state == "8"
    polls = mock_fetch.await_count

    today.move_to("2026-10-26 07:00:01+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert _state(hass, entity_id).state == "7"
    assert mock_fetch.await_count == polls
