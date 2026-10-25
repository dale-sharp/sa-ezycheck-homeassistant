# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Coordinator that polls the registration check for one plate."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SaEzycheckClient,
    SaEzycheckData,
    SaEzycheckError,
    SaEzycheckInvalidPlateError,
    parse_payload,
)
from .const import (
    CONF_PLATE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    ISSUE_PERSISTENT_FETCH_FAILURE,
    OPTION_SCAN_INTERVAL_MINUTES,
    PERSISTENT_FETCH_FAILURE_THRESHOLD,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import SaEzycheckConfigEntry

_LOGGER = logging.getLogger(__name__)


class SaEzycheckCoordinator(DataUpdateCoordinator[SaEzycheckData]):
    """Polls the API and shares the result with every entity."""

    config_entry: SaEzycheckConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SaEzycheckConfigEntry) -> None:
        """Initialise the coordinator from the config entry."""
        interval_minutes = entry.options.get(
            OPTION_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self._client = SaEzycheckClient(
            async_get_clientsession(hass),
        )
        self._plate: str = entry.data[CONF_PLATE]
        # Consecutive failed updates since the last success.
        self._consecutive_failures = 0

    async def _async_update_data(self) -> SaEzycheckData:
        """Fetch and parse the latest data."""
        try:
            raw = await self._client.async_fetch_raw(self._plate)
            data = await self.hass.async_add_executor_job(
                parse_payload, raw, self._plate
            )
        except SaEzycheckInvalidPlateError as err:
            self._register_failure()
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_plate",
                translation_placeholders={"plate": self._plate},
            ) from err
        except SaEzycheckError as err:
            self._register_failure()
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err

        self._clear_failure()
        return data

    def _register_failure(self) -> None:
        """Count a failed update and raise a repair issue once failures persist."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= PERSISTENT_FETCH_FAILURE_THRESHOLD:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_PERSISTENT_FETCH_FAILURE}_{self.config_entry.entry_id}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_PERSISTENT_FETCH_FAILURE,
                translation_placeholders={
                    "entry_title": self.config_entry.title,
                    "threshold": str(PERSISTENT_FETCH_FAILURE_THRESHOLD),
                },
            )

    def _clear_failure(self) -> None:
        """Reset the failure counter and clear any repair issue after a success."""
        if self._consecutive_failures > 0:
            ir.async_delete_issue(
                self.hass,
                DOMAIN,
                f"{ISSUE_PERSISTENT_FETCH_FAILURE}_{self.config_entry.entry_id}",
            )
            self._consecutive_failures = 0
