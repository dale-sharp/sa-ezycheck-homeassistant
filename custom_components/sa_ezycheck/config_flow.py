# Copyright (C) 2026 dale-sharp
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plate entry, plate reconfiguration and scan interval options flows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

if TYPE_CHECKING:
    import probatio as vol
else:
    try:
        # Home Assistant 2026.9+ validates with probatio, an API-compatible
        # replacement for voluptuous, and types `data_schema` against it.
        import probatio as vol
    except ImportError:  # pragma: no cover - Home Assistant < 2026.9
        import voluptuous as vol

from .api import (
    SaEzycheckClient,
    SaEzycheckError,
    SaEzycheckInvalidPlateError,
    is_valid_plate,
    normalise_plate,
    parse_payload,
)
from .const import (
    CONF_PLATE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    OPTION_SCAN_INTERVAL_MINUTES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


def _plate_schema(plate: str = "") -> vol.Schema:
    """Return the form schema for setup and reconfigure."""
    return vol.Schema({vol.Required(CONF_PLATE, default=plate): TextSelector()})


def _interval_schema(scan_interval: int) -> vol.Schema:
    """Return the options form schema."""
    return vol.Schema(
        {
            vol.Required(
                OPTION_SCAN_INTERVAL_MINUTES, default=scan_interval
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_MINUTES,
                    max=MAX_SCAN_INTERVAL_MINUTES,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="minutes",
                )
            )
        }
    )


async def _async_validate_plate(hass: HomeAssistant, plate: str) -> str | None:
    """Check the plate with the service; return an error code, or None if valid."""
    if not is_valid_plate(plate):
        return "invalid_plate"
    client = SaEzycheckClient(async_get_clientsession(hass))
    try:
        raw = await client.async_fetch_raw(plate)
        await hass.async_add_executor_job(parse_payload, raw, plate)
    except SaEzycheckInvalidPlateError:
        return "invalid_plate"
    except SaEzycheckError:
        return "cannot_connect"
    return None


class SaEzycheckConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: check the plate before creating the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            plate = normalise_plate(user_input[CONF_PLATE])
            await self.async_set_unique_id(plate)
            self._abort_if_unique_id_configured()
            error = await _async_validate_plate(self.hass, plate)
            if error is None:
                return self.async_create_entry(
                    title=plate,
                    data={CONF_PLATE: plate},
                    options={
                        OPTION_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES
                    },
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=_plate_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user correct the plate without removing the entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            plate = normalise_plate(user_input[CONF_PLATE])
            await self.async_set_unique_id(plate)
            self._abort_if_unique_id_configured()
            error = await _async_validate_plate(self.hass, plate)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=plate,
                    title=plate,
                    data_updates={CONF_PLATE: plate},
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_plate_schema(entry.data[CONF_PLATE]),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SaEzycheckOptionsFlow:  # noqa: ARG004
        """Create the options flow."""
        return SaEzycheckOptionsFlow()


class SaEzycheckOptionsFlow(OptionsFlowWithReload):
    """Handle the options flow; the entry reloads when the options change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    OPTION_SCAN_INTERVAL_MINUTES: user_input[
                        OPTION_SCAN_INTERVAL_MINUTES
                    ]
                }
            )
        current = self.config_entry.options.get(
            OPTION_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        return self.async_show_form(
            step_id="init", data_schema=_interval_schema(current)
        )
