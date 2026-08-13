"""Diagnostics: the last poll's outcome plus the raw register map."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.waterfurnace_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import ConnectionFactory


async def test_diagnostics_carry_the_whole_register_map(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """An issue report needs the setup-only blocks as much as the polled ones."""
    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["failed"] == {}
    assert "compressor" in diagnostics["updated"]
    holding = diagnostics["registers"]["holding"]
    assert holding[2] == 305  # identity: read at setup, never polled
    assert holding[16] == 244  # status: polled
    json.dumps(diagnostics)  # the payload is downloaded as JSON


async def test_diagnostics_name_the_sub_system_that_failed(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Which sub-system was stale is the first thing to look at in a report."""
    coordinator = config_entry.runtime_data
    mock_connection.unit.fail_read(3000, ModbusTimeoutError("slow drive block"))
    await coordinator.async_refresh()

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert "compressor" in diagnostics["failed"]
    assert "compressor" not in diagnostics["updated"]
    # The block that failed the poll refuses the raw read too.
    assert "error" in diagnostics["registers"]
