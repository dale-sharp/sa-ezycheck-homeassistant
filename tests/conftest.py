"""Shared fixtures for the test suite."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_ezycheck.const import (
    CONF_PLATE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAIN_DEVICE_ID,
    OPTION_SCAN_INTERVAL_MINUTES,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Where the HTTP boundary is patched: the real parsing and coordinator code runs.
FETCH_TARGET = "custom_components.sa_ezycheck.api.SaEzycheckClient.async_fetch_raw"
PLATE = "ABC123"
USER_INPUT = {CONF_PLATE: PLATE}

# The only device of a vehicle entry.
FIRST_DEVICE_ID = MAIN_DEVICE_ID

# What the service answers for a plate it rejects.
INVALID_PLATE_RESPONSE = (
    "<rtnmsg><apiVersion>1</apiVersion><msgs><plate>null</plate>"
    "<rst>Invalid plate format, please check the plate number and try again.</rst>"
    "</msgs></rtnmsg>"
)

_RECORD_DEFAULTS: dict[str, str | None] = {
    "plate": PLATE,
    "plateType": "ALPHANUMERIC",
    "make": "FORD",
    "bodyType": "SEDAN",
    "primaryColour": "ORANGE",
    "expiryDate": "02/11/2026",
    "premiumClass": "1 - CARS (SEDAN, STN WAGON, ETC)",
    "ctpInsurer": "NRMA",
    "inspectionExpired": "YES",
    "maskedVin": "**************0000",
    "incidentInd": "NO",
    "pendingSuspensionInd": "NO",
}


def record_xml(**fields: str | None) -> str:
    """Build one ``<msgs>`` record; a value of None leaves the element out."""
    merged = {**_RECORD_DEFAULTS, **fields}
    body = "".join(
        f"<{tag}>{value}</{tag}>" for tag, value in merged.items() if value is not None
    )
    return f"<msgs>{body}</msgs>"


def response_xml(*records: str) -> str:
    """Wrap records in the service's response envelope."""
    return f"<rtnmsg><apiVersion>1</apiVersion>{''.join(records)}</rtnmsg>"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for every test in the suite."""


@pytest.fixture(autouse=True)
def today(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Pin the clock so day counts are stable: 8 days before the fixture's expiry."""
    freezer.move_to("2026-10-25 12:00:00+00:00")
    return freezer


@pytest.fixture(autouse=True)
def suppress_expected_log_noise() -> Generator[None]:
    """
    Raise log levels for loggers that produce expected noise during tests.

    - homeassistant.loader and homeassistant.setup log for every custom integration
      they load; expected in all tests and not actionable.
    - custom_components.sa_ezycheck logs coordinator failures that tests provoke on purpose.
    """
    loggers = [
        logging.getLogger("homeassistant.loader"),
        logging.getLogger("homeassistant.setup"),
        logging.getLogger("custom_components.sa_ezycheck"),
    ]
    original_levels = [(logger, logger.level) for logger in loggers]
    for logger in loggers:
        logger.setLevel(logging.CRITICAL)
    yield
    for logger, level in original_levels:
        logger.setLevel(level)


@pytest.fixture
def payload_text() -> str:
    """Return the sample API response."""
    return (FIXTURES_DIR / "payload.xml").read_text(encoding="utf-8")


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry as the config flow would create it."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=PLATE,
        unique_id=PLATE,
        data={CONF_PLATE: PLATE},
        options={OPTION_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES},
    )


@pytest.fixture
def mock_fetch(payload_text: str) -> Generator[AsyncMock]:
    """Patch the HTTP boundary to return the sample payload."""
    with patch(FETCH_TARGET, new_callable=AsyncMock, return_value=payload_text) as mock:
        yield mock


@pytest.fixture
async def init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_fetch: AsyncMock
) -> MockConfigEntry:
    """Set up the integration with the sample payload and return its entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    return mock_config_entry
