"""Tests for api.py: payload parsing and the HTTP client."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.sa_ezycheck.api import (
    SaEzycheckClient,
    SaEzycheckConnectionError,
    SaEzycheckInvalidPlateError,
    is_valid_plate,
    normalise_plate,
    parse_payload,
)
from custom_components.sa_ezycheck.const import API_URL, MAIN_DEVICE_ID

from .conftest import INVALID_PLATE_RESPONSE, PLATE, record_xml, response_xml

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )


def _client(hass: HomeAssistant) -> SaEzycheckClient:
    return SaEzycheckClient(
        async_get_clientsession(hass),
    )


def _device(raw: str):
    return parse_payload(raw, PLATE).devices[MAIN_DEVICE_ID]


def test_parse_payload_maps_the_vehicle(payload_text: str) -> None:
    data = parse_payload(payload_text, PLATE)

    assert set(data.devices) == {MAIN_DEVICE_ID}
    device = data.devices[MAIN_DEVICE_ID]
    assert device.name == PLATE
    assert device.manufacturer == "FORD"
    assert device.model == "SEDAN"
    assert device.values == {
        "make": "FORD",
        "body_type": "SEDAN",
        "primary_colour": "ORANGE",
        "plate_type": "ALPHANUMERIC",
        "premium_class": "1 - CARS (SEDAN, STN WAGON, ETC)",
        "ctp_insurer": "NRMA",
        "masked_vin": "**************0000",
        "expiry_date": date(2026, 11, 2),
        "inspection_due_date": None,
        "inspection_expired": True,
        "incident": False,
        "pending_suspension": False,
        "registered": True,
    }
    assert device.attributes == {}


def test_parse_payload_exposes_filled_in_details_as_attributes() -> None:
    device = _device(
        response_xml(
            record_xml(
                conditionalDetails="NIGHT ONLY",
                vehicleConditions="LIGHT TRAILER",
                inspectionDueDate="01/12/2026",
            )
        )
    )

    assert device.attributes == {
        "conditional_details": "NIGHT ONLY",
        "vehicle_conditions": "LIGHT TRAILER",
    }
    assert device.values["inspection_due_date"] == date(2026, 12, 1)


def test_parse_payload_prefers_the_latest_registered_vehicle() -> None:
    device = _device(
        response_xml(
            record_xml(make="NISSAN", expiryDate="UNREGISTERED"),
            record_xml(make="BYD", expiryDate="30/11/2026"),
            record_xml(make="MAZDA", expiryDate="30/11/2025"),
        )
    )

    assert device.manufacturer == "BYD"
    assert device.values["expiry_date"] == date(2026, 11, 30)
    assert device.values["registered"] is True


def test_parse_payload_reports_an_unregistered_vehicle() -> None:
    device = _device(
        response_xml(
            record_xml(make="NISSAN", expiryDate="UNREGISTERED"),
            record_xml(make="BYD", expiryDate="UNREGISTERED"),
        )
    )

    assert device.manufacturer == "NISSAN"
    assert device.values["expiry_date"] is None
    assert device.values["registered"] is False


def test_parse_payload_treats_unreadable_dates_and_flags_as_unknown() -> None:
    device = _device(
        response_xml(
            record_xml(expiryDate="32/13/2026", incidentInd="MAYBE", maskedVin=None)
        )
    )

    assert device.values["expiry_date"] is None
    assert device.values["incident"] is None
    assert device.values["pending_suspension"] is False
    assert device.values["masked_vin"] is None


def test_parse_payload_rejects_a_plate_the_service_refuses() -> None:
    with pytest.raises(SaEzycheckInvalidPlateError, match="Invalid plate format"):
        parse_payload(INVALID_PLATE_RESPONSE, PLATE)


@pytest.mark.parametrize(
    "raw",
    [
        "not xml",
        "<rtnmsg/>",
        "<rtnmsg><msgs><plate>null</plate></msgs></rtnmsg>",
    ],
)
def test_parse_payload_rejects_unexpected_responses(raw: str) -> None:
    with pytest.raises(SaEzycheckConnectionError):
        parse_payload(raw, PLATE)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("abc123", "ABC123"),
        (" s 123-abc ", "S123ABC"),
        ("S123·ABC", "S123ABC"),
        ("s.123.abc", "S123ABC"),
        ("", ""),
    ],
)
def test_normalise_plate(value: str, expected: str) -> None:
    assert normalise_plate(value) == expected


@pytest.mark.parametrize(
    "plate",
    [
        "S",  # custom: one letter
        "ABCDEFG",  # custom: seven letters
        "A1B2C3D",  # custom: letters and numbers, seven characters
        "JAPAN1",  # Japanese custom: up to six, at least one letter
        "ABC123",  # personalised and 1966 standard
        "AB1234",  # personalised
        "ABCD12",  # personalised
        "RAA123",  # classic
        "SUR999",  # classic
        "S123ABC",  # standard since 2008
        "S12ABC",  # motorcycle since 2008
        "AA123A",  # premium
        "SB00AA",  # heavy vehicle
        "RA123",  # motorcycle, five characters
        "12345",  # pre-1966, five digits
        "123456",  # pre-1966, six digits
        "TAXI12",  # also a valid custom plate
        "TAXI123",  # metropolitan taxi
        "TAXI1234",  # metropolitan taxi, eight characters
    ],
)
def test_is_valid_plate_accepts_the_plate_formats(plate: str) -> None:
    assert is_valid_plate(plate)


@pytest.mark.parametrize(
    "plate",
    [
        "",  # nothing
        "1",  # custom plates need a letter
        "1234",  # too short for a numbers-only plate
        "1234567",  # numbers-only plates stop at six digits
        "ABCDEFGH",  # custom plates stop at seven characters
        "TAXI12345",  # nine characters
        "AB-123",  # separators are removed by normalise_plate, not accepted here
        "ABC 123",
        "ABC12!",
        "abc123",  # must already be upper case
        "ÄBC123",
    ],
)
def test_is_valid_plate_rejects_everything_else(plate: str) -> None:
    assert not is_valid_plate(plate)


async def test_fetch_raw_returns_the_response_body(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, payload_text: str
) -> None:
    aioclient_mock.get(API_URL, text=payload_text)

    assert await _client(hass).async_fetch_raw(PLATE) == payload_text
    assert aioclient_mock.mock_calls[0][1].query["plate"] == PLATE


async def test_fetch_raw_wraps_http_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(API_URL, status=500)

    with pytest.raises(SaEzycheckConnectionError):
        await _client(hass).async_fetch_raw(PLATE)


async def test_fetch_raw_wraps_timeouts(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(API_URL, exc=TimeoutError)

    with pytest.raises(SaEzycheckConnectionError):
        await _client(hass).async_fetch_raw(PLATE)
