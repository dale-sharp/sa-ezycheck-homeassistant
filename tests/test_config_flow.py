"""Tests for config_flow.py: setup, reconfigure and options flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sa_ezycheck.api import SaEzycheckConnectionError
from custom_components.sa_ezycheck.const import (
    CONF_PLATE,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAIN_DEVICE_ID,
    MIN_SCAN_INTERVAL_MINUTES,
    OPTION_SCAN_INTERVAL_MINUTES,
    device_identifier,
)

from .conftest import FETCH_TARGET, INVALID_PLATE_RESPONSE, PLATE, USER_INPUT

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

SETUP_ENTRY = "custom_components.sa_ezycheck.async_setup_entry"


async def _start_user_flow(hass: HomeAssistant) -> ConfigFlowResult:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_fetch: AsyncMock
) -> None:
    with patch(SETUP_ENTRY, return_value=True):
        result = await _start_user_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PLATE: " abc-123 "}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == PLATE
    assert result["data"] == {CONF_PLATE: PLATE}
    assert result["options"] == {
        OPTION_SCAN_INTERVAL_MINUTES: DEFAULT_SCAN_INTERVAL_MINUTES
    }
    assert result["result"].unique_id == PLATE
    mock_fetch.assert_awaited_once_with(PLATE)


async def test_user_flow_rejects_a_malformed_plate_without_asking_the_service(
    hass: HomeAssistant, mock_fetch: AsyncMock
) -> None:
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PLATE: "TOO LONG 99"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_plate"}
    mock_fetch.assert_not_awaited()


async def test_user_flow_reports_a_plate_the_service_refuses(
    hass: HomeAssistant, mock_fetch: AsyncMock
) -> None:
    mock_fetch.return_value = INVALID_PLATE_RESPONSE
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_plate"}


async def test_user_flow_reports_cannot_connect_and_recovers(
    hass: HomeAssistant, mock_fetch: AsyncMock
) -> None:
    mock_fetch.side_effect = SaEzycheckConnectionError("down")
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_fetch.side_effect = None
    with patch(SETUP_ENTRY, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_aborts_when_the_plate_is_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PLATE: "abc 123"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_fetch.assert_not_awaited()


async def test_reconfigure_flow_changes_the_plate(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["data_schema"] is not None
    assert result["data_schema"]({})[CONF_PLATE] == PLATE

    with patch(SETUP_ENTRY, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PLATE: "xyz789"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {CONF_PLATE: "XYZ789"}
    assert mock_config_entry.unique_id == "XYZ789"
    assert mock_config_entry.title == "XYZ789"


async def test_reconfigure_flow_aborts_when_another_entry_has_the_plate(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_fetch: AsyncMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, unique_id="XYZ789", data={CONF_PLATE: "XYZ789"}, title="XYZ789"
    ).add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PLATE: "XYZ789"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data == {CONF_PLATE: PLATE}


@pytest.mark.parametrize(
    ("side_effect", "return_value", "error"),
    [
        (SaEzycheckConnectionError("down"), None, "cannot_connect"),
        (None, INVALID_PLATE_RESPONSE, "invalid_plate"),
    ],
)
async def test_reconfigure_flow_reports_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    side_effect: Exception | None,
    return_value: str | None,
    error: str,
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)

    with patch(
        FETCH_TARGET,
        new_callable=AsyncMock,
        side_effect=side_effect,
        return_value=return_value,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PLATE: "XYZ789"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_options_flow_updates_the_scan_interval_and_reloads(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload",
        wraps=hass.config_entries.async_reload,
    ) as mock_reload:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={OPTION_SCAN_INTERVAL_MINUTES: 90}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.options[OPTION_SCAN_INTERVAL_MINUTES] == 90
    mock_reload.assert_called_once_with(init_integration.entry_id)


async def test_options_flow_prefills_the_current_interval(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={OPTION_SCAN_INTERVAL_MINUTES: 90}
    )

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["data_schema"] is not None
    assert result["data_schema"]({})[OPTION_SCAN_INTERVAL_MINUTES] == 90


async def test_options_flow_prefills_the_default_for_an_entry_without_options(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="NOOPTS", data={CONF_PLATE: "NOOPTS"}, options={}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["data_schema"] is not None
    assert (
        result["data_schema"]({})[OPTION_SCAN_INTERVAL_MINUTES]
        == DEFAULT_SCAN_INTERVAL_MINUTES
    )


@pytest.mark.regression
async def test_flow_manager_rejects_invalid_scan_interval(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """
    Invalid input is reported by the flow manager as InvalidData.

    Home Assistant 2026.9+ validates with probatio, so this only holds if the
    schema's errors are the engine's own `Invalid` type.
    """
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={OPTION_SCAN_INTERVAL_MINUTES: MIN_SCAN_INTERVAL_MINUTES - 1},
        )


@pytest.mark.regression
async def test_config_flow_form_serialises_for_frontend(
    hass: HomeAssistant, hass_client
) -> None:
    """The user-step form is serialised through the frontend's REST API."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()

    response = await client.post(
        "/api/config/config_entries/flow", json={"handler": DOMAIN}
    )

    assert response.status == 200
    body = await response.json()
    assert body["type"] == "form"
    assert body["step_id"] == "user"
    assert {field["name"] for field in body["data_schema"]} == set(USER_INPUT)


async def test_reconfigure_flow_renames_the_device_of_a_loaded_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    result = await init_integration.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PLATE: "XYZ789"}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    device = dr.async_get(hass).async_get_device_by_identifier(
        device_identifier(init_integration.entry_id, MAIN_DEVICE_ID),
        init_integration.entry_id,
    )
    assert device is not None
    assert device.name == "XYZ789"
