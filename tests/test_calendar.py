# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for calendar.py: the registration and inspection events."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.sa_ezycheck.calendar import CALENDARS, SaEzycheckCalendar
from custom_components.sa_ezycheck.const import DOMAIN, entity_unique_id

from .conftest import FIRST_DEVICE_ID, PLATE, record_xml, response_xml

if TYPE_CHECKING:
    from unittest.mock import AsyncMock

    from homeassistant.core import HomeAssistant, State
    from pytest_homeassistant_custom_component.common import MockConfigEntry


def _entity_id(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, entity_unique_id(entry.entry_id, FIRST_DEVICE_ID, key)
    )
    assert entity_id is not None
    return entity_id


def _state(hass: HomeAssistant, entity_id: str) -> State:
    state = hass.states.get(entity_id)
    assert state is not None
    return state


def _local(hass: HomeAssistant, day: tuple[int, int, int]) -> datetime:
    return datetime(*day, tzinfo=dt_util.get_default_time_zone())


async def test_registration_calendar_shows_the_next_expiry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    entity_id = _entity_id(hass, init_integration, "registration")
    state = _state(hass, entity_id)

    assert entity_id == f"calendar.{PLATE.lower()}_registration"
    assert state.state == STATE_OFF
    assert state.attributes["message"] == f"{PLATE} registration expires"
    assert state.attributes["all_day"] is True
    assert state.attributes["start_time"] == "2026-11-02 00:00:00"
    assert state.attributes["end_time"] == "2026-11-03 00:00:00"


async def test_registration_event_is_active_on_the_expiry_day(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_fetch: AsyncMock,
) -> None:
    mock_fetch.return_value = response_xml(record_xml(expiryDate="25/10/2026"))
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = _state(hass, _entity_id(hass, init_integration, "registration"))

    assert state.state == STATE_ON


@pytest.mark.parametrize("expiry", ["24/10/2026", "UNREGISTERED"])
async def test_registration_calendar_has_no_event_when_past_or_unregistered(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_fetch: AsyncMock,
    expiry: str,
) -> None:
    mock_fetch.return_value = response_xml(record_xml(expiryDate=expiry))
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = _state(hass, _entity_id(hass, init_integration, "registration"))

    assert state.state == STATE_OFF
    assert "message" not in state.attributes


@pytest.mark.parametrize(
    ("start", "end", "count"),
    [
        ((2026, 11, 1), (2026, 11, 3), 1),
        ((2026, 11, 2), (2026, 11, 3), 1),
        ((2026, 10, 1), (2026, 11, 2), 0),
        ((2026, 11, 3), (2026, 12, 1), 0),
    ],
)
async def test_get_events_returns_the_event_only_inside_the_range(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    count: int,
) -> None:
    entity = hass.data["calendar"].get_entity(
        _entity_id(hass, init_integration, "registration")
    )

    events = await entity.async_get_events(hass, _local(hass, start), _local(hass, end))

    assert len(events) == count
    if count:
        assert events[0].start == date(2026, 11, 2)
        assert events[0].end == date(2026, 11, 2) + timedelta(days=1)


async def test_calendar_has_no_event_when_the_vehicle_is_no_longer_reported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    coordinator = init_integration.runtime_data
    entity = SaEzycheckCalendar(coordinator, FIRST_DEVICE_ID, CALENDARS[0])
    assert entity.event is not None

    coordinator.data = replace(coordinator.data, devices={})

    assert entity.event is None
    assert not entity.available
    assert (
        await entity.async_get_events(
            hass, _local(hass, (2026, 1, 1)), _local(hass, (2027, 1, 1))
        )
        == []
    )


async def test_inspection_calendar_is_disabled_by_default(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    entity_id = _entity_id(hass, init_integration, "inspection")
    registry_entry = er.async_get(hass).async_get(entity_id)

    assert registry_entry is not None
    assert registry_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None


async def test_inspection_calendar_shows_the_due_date_once_enabled(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_fetch: AsyncMock,
) -> None:
    mock_fetch.return_value = response_xml(record_xml(inspectionDueDate="01/12/2026"))
    entity_id = _entity_id(hass, init_integration, "inspection")
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(init_integration.entry_id)
    await hass.async_block_till_done()

    state = _state(hass, entity_id)

    assert state.attributes["message"] == f"{PLATE} inspection due"
    assert state.attributes["start_time"] == "2026-12-01 00:00:00"


async def test_inspection_calendar_has_no_event_without_a_due_date(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    entity_id = _entity_id(hass, init_integration, "inspection")
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(init_integration.entry_id)
    await hass.async_block_till_done()

    state = _state(hass, entity_id)

    assert state.state == STATE_OFF
    assert "message" not in state.attributes
