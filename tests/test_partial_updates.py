"""One sub-system the ABC will not answer must not blank the whole heat pump.

The library reads the sub-systems separately and reports which ones failed; the
entities reading a failed one go unavailable while the rest keep updating.
"""

from __future__ import annotations

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import ConnectionFactory

ENTERING_WATER = "sensor.ndv049a111_entering_water_temperature"
COMPRESSOR_SPEED = "sensor.ndv049a111_compressor_speed"
LINE_VOLTAGE = "sensor.ndv049a111_line_voltage"
COMPRESSOR_RUNNING = "binary_sensor.ndv049a111_compressor"
THERMOSTAT = "climate.ndv049a111"


async def test_a_failed_sub_system_only_blanks_its_own_entities(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Register 3000 is the VS drive's block; nothing else is read from it."""
    coordinator = config_entry.runtime_data
    unit = mock_connection.unit
    assert hass.states.get(COMPRESSOR_SPEED).state == "5"

    unit.holding[1111] = 550  # entering water rises to 55.0 on the device
    unit.fail_read(3000, ModbusTimeoutError("slow drive block"))
    await coordinator.async_refresh()

    assert hass.states.get(COMPRESSOR_SPEED).state == STATE_UNAVAILABLE
    assert hass.states.get(ENTERING_WATER).state == "55.0"
    assert coordinator.last_update_success


async def test_the_status_block_carries_the_thermostat_action(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """hvac_action reads the outputs word, so the thermostat depends on status.

    Status is the poll's probe, so it is refused rather than timed out: a
    refusal proves the heat pump is there and leaves the rest of the poll to run.
    """
    coordinator = config_entry.runtime_data
    mock_connection.unit.fail_read(16, IllegalDataAddressError())
    await coordinator.async_refresh()

    assert hass.states.get(LINE_VOLTAGE).state == STATE_UNAVAILABLE
    assert hass.states.get(COMPRESSOR_RUNNING).state == STATE_UNAVAILABLE
    assert hass.states.get(THERMOSTAT).state == STATE_UNAVAILABLE
    assert hass.states.get(ENTERING_WATER).state == "50.0"


async def test_a_failed_zone_leaves_the_other_zone_alone(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Zone entities are numbered the way the report keys the zones."""
    coordinator = config_entry.runtime_data
    mock_connection.unit.fail_read(31010, ModbusTimeoutError("slow zone 2"))
    await coordinator.async_refresh()

    assert hass.states.get("climate.ndv049a111_zone_2").state == STATE_UNAVAILABLE
    assert hass.states.get("climate.ndv049a111_zone_1").state != STATE_UNAVAILABLE


async def test_a_failed_sub_system_is_logged_when_it_starts_failing(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A block that stays refused would otherwise log on every poll, forever."""
    coordinator = config_entry.runtime_data
    mock_connection.unit.fail_read(3000, ModbusTimeoutError("slow drive block"))

    await coordinator.async_refresh()
    assert "Failed to fetch compressor" in caplog.text

    caplog.clear()
    await coordinator.async_refresh()
    assert "Failed to fetch compressor" not in caplog.text


async def test_a_poll_that_answered_nothing_fails_with_a_reason(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Home Assistant logs only the message, so it has to name a real failure.

    Every sub-system refusing is a heat pump that answers but serves nothing;
    a heat pump that answers nothing at all raises instead, and is covered by
    ``test_a_stuck_link_is_recycled_after_repeated_timeouts``.
    """
    coordinator = config_entry.runtime_data
    mock_connection.unit.fail_requests(IllegalDataAddressError())

    await coordinator.async_refresh()

    assert not coordinator.last_update_success
    err = coordinator.last_exception
    # Every sub-system's error stays reachable behind the one that is quoted.
    assert isinstance(err.__cause__, ExceptionGroup)
    assert len(err.__cause__.exceptions) > 1


async def test_entities_come_back_once_the_block_answers_again(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """A failed sub-system is a per-poll verdict, not a latch."""
    coordinator = config_entry.runtime_data
    unit = mock_connection.unit

    unit.fail_read(3000, ModbusTimeoutError("slow drive block"))
    await coordinator.async_refresh()
    assert hass.states.get(COMPRESSOR_SPEED).state == STATE_UNAVAILABLE

    unit.fail_read(3000, None)
    unit.holding[3001] = 8
    await coordinator.async_refresh()
    assert hass.states.get(COMPRESSOR_SPEED).state == "8"
