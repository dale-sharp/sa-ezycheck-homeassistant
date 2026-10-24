"""API client and data models for the integration."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import aiohttp

from .const import API_TIMEOUT, API_URL, MAIN_DEVICE_ID

if TYPE_CHECKING:
    from collections.abc import Mapping
    from xml.etree.ElementTree import Element

# South Australian plate rules, applied to a normalised plate (upper case, no spaces):
# - custom: letters only, or letters and numbers, 1 to 7 characters. This also covers
#   the Japanese custom (up to 6, at least one letter), personalised (letters then at
#   least one number, 6) and classic (three letters from R, S or U, then three
#   numbers) rules, and every modern standard format (S000AAA, AAA000, S00AAA, ...).
# - pre-1966 plates: numbers only, 5 or 6 digits.
# - metropolitan taxis: TAXI followed by 3 or 4 numbers.
_PLATE_RULES = re.compile(r"(?=.*[A-Z])[A-Z0-9]{1,7}|[0-9]{5,6}|TAXI[0-9]{3,4}")

# Output key -> XML element, for the values the integration exposes.
_TEXT_FIELDS = {
    "make": "make",
    "body_type": "bodyType",
    "primary_colour": "primaryColour",
    "plate_type": "plateType",
    "premium_class": "premiumClass",
    "ctp_insurer": "ctpInsurer",
    "masked_vin": "maskedVin",
}
_DATE_FIELDS = {
    "expiry_date": "expiryDate",
    "inspection_due_date": "inspectionDueDate",
}
_FLAG_FIELDS = {
    "inspection_expired": "inspectionExpired",
    "incident": "incidentInd",
    "pending_suspension": "pendingSuspensionInd",
}
# Free-text details that are empty for most vehicles; exposed only when filled in.
_ATTRIBUTE_FIELDS = {
    "conditional_details": "conditionalDetails",
    "registered_configuration": "registeredConfiguration",
    "registered_gvm_gcm": "registeredGvmGcm",
    "manufacturer_gvm_gcm": "manufacturerGvmGcm",
    "vehicle_conditions": "vehicleConditions",
    "inspection_type": "inspectionType",
}


class SaEzycheckError(Exception):
    """Base error for the API client."""


class SaEzycheckConnectionError(SaEzycheckError):
    """The API could not be reached or returned an unusable response."""


class SaEzycheckInvalidPlateError(SaEzycheckError):
    """The API rejected the plate number."""


@dataclass(frozen=True)
class DeviceData:
    """Values reported for one device (one vehicle)."""

    name: str
    manufacturer: str | None = None
    model: str | None = None
    values: Mapping[str, str | bool | date | None] = field(default_factory=dict)
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SaEzycheckData:
    """A snapshot of everything the API reported."""

    devices: Mapping[str, DeviceData] = field(default_factory=dict)


def normalise_plate(value: str) -> str:
    """Return the plate upper-cased, without the spaces, hyphens or dots plates show."""
    return re.sub(r"[\s.\-·]", "", value).upper()


def is_valid_plate(plate: str) -> bool:
    """Return whether a normalised plate follows a South Australian plate format."""
    return _PLATE_RULES.fullmatch(plate) is not None


def _text(record: Element, tag: str) -> str | None:
    """Return an element's stripped text, or None when it is missing or empty."""
    return (record.findtext(tag) or "").strip() or None


def _parse_date(value: str | None) -> date | None:
    """Parse a dd/mm/yyyy date; anything else (such as UNREGISTERED) is None."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()  # noqa: DTZ007
    except ValueError:
        return None


def _parse_flag(value: str | None) -> bool | None:
    """Parse a YES/NO flag; anything else is unknown."""
    if value is None:
        return None
    return {"YES": True, "NO": False}.get(value.upper())


def _select_record(records: list[Element]) -> Element:
    """
    Pick the vehicle that currently holds the plate.

    A plate that moved between vehicles is reported once per vehicle; the registered
    one has a real expiry date, and the latest date wins when several do.
    """
    dated = [
        (expiry, record)
        for record in records
        if (expiry := _parse_date(_text(record, "expiryDate"))) is not None
    ]
    if dated:
        return max(dated, key=lambda pair: pair[0])[1]
    return records[0]


def parse_payload(raw: str, plate: str) -> SaEzycheckData:
    """
    Parse the raw API response.

    Synchronous and potentially CPU-bound: call it through
    ``hass.async_add_executor_job`` so it never runs on the event loop.
    """
    try:
        # The body comes from a fixed HTTPS endpoint; expat does not resolve external
        # entities, so the standard parser is sufficient.
        root = ET.fromstring(raw)  # noqa: S314
    except ET.ParseError as err:
        message = f"Unexpected response from the API: {err}"
        raise SaEzycheckConnectionError(message) from err

    messages = root.findall("msgs")
    vehicles = [record for record in messages if record.find("expiryDate") is not None]
    if not vehicles:
        for record in messages:
            if rejection := _text(record, "rst"):
                raise SaEzycheckInvalidPlateError(rejection)
        message = "Unexpected response from the API: no vehicle in the response"
        raise SaEzycheckConnectionError(message)

    record = _select_record(vehicles)
    expiry = _parse_date(_text(record, "expiryDate"))
    values: dict[str, str | bool | date | None] = {
        key: _text(record, tag) for key, tag in _TEXT_FIELDS.items()
    }
    values.update(
        {key: _parse_date(_text(record, tag)) for key, tag in _DATE_FIELDS.items()}
    )
    values.update(
        {key: _parse_flag(_text(record, tag)) for key, tag in _FLAG_FIELDS.items()}
    )
    values["registered"] = expiry is not None
    attributes = {
        key: text
        for key, tag in _ATTRIBUTE_FIELDS.items()
        if (text := _text(record, tag))
    }
    device = DeviceData(
        name=plate,
        manufacturer=_text(record, "make"),
        model=_text(record, "bodyType"),
        values=values,
        attributes=attributes,
    )
    return SaEzycheckData(devices={MAIN_DEVICE_ID: device})


class SaEzycheckClient:
    """Thin async client for South Australia's public registration check."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialise the client with Home Assistant's shared web session."""
        self._session = session

    async def async_fetch_raw(self, plate: str) -> str:
        """Fetch the raw response body for a plate."""
        try:
            async with asyncio.timeout(API_TIMEOUT):
                response = await self._session.get(API_URL, params={"plate": plate})
                response.raise_for_status()
                body = await response.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            message = f"Error talking to the API: {err}"
            raise SaEzycheckConnectionError(message) from err
        return body
