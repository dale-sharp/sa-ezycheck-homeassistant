# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Domain, endpoint URL and scan interval limits for SA EzyCheck."""

from __future__ import annotations

from typing import Final

DOMAIN = "sa_ezycheck"

API_URL: Final[str] = (
    "https://www.ecom.transport.sa.gov.au/et/CheckRegistrationExpiryDateServlet"
)
API_TIMEOUT: Final[int] = 30  # seconds

CONF_PLATE: Final[str] = "plate"

DEFAULT_SCAN_INTERVAL_MINUTES: Final[int] = 720
# Registration data changes at most a few times a year; the floor keeps the load on the
# public service low.
MIN_SCAN_INTERVAL_MINUTES: Final[int] = 60
MAX_SCAN_INTERVAL_MINUTES: Final[int] = 1440

OPTION_SCAN_INTERVAL_MINUTES: Final[str] = "scan_interval_minutes"

PERSISTENT_FETCH_FAILURE_THRESHOLD: Final[int] = 3
ISSUE_PERSISTENT_FETCH_FAILURE: Final[str] = "persistent_fetch_failure"

# Each config entry is one vehicle with a single device.
MAIN_DEVICE_ID: Final[str] = "main"


def device_identifier(entry_id: str, device_id: str) -> tuple[str, str]:
    """Return the device-registry identifier for a device of a config entry."""
    return (DOMAIN, f"{entry_id}_{device_id}")


def entity_unique_id(entry_id: str, device_id: str, key: str) -> str:
    """Return the unique ID of an entity, scoped by config entry."""
    return f"{entry_id}_{device_id}_{key}"
