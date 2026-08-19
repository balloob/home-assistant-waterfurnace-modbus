"""Entity tests: decoded states and the write paths."""

from __future__ import annotations

import pytest
from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HVAC_ACTION,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.water_heater import (
    ATTR_OPERATION_MODE,
    DOMAIN as WATER_HEATER_DOMAIN,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE as WH_SET_TEMPERATURE,
    STATE_ELECTRIC,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import ConnectionFactory

THERMOSTAT = "climate.ndv049a111"
DHW = "water_heater.ndv049a111_hot_water"


async def test_sensor_states(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Registers decode into sensor states with the right units."""
    entering_water = hass.states.get("sensor.ndv049a111_entering_water_temperature")
    assert entering_water.state == "50.0"
    assert entering_water.attributes["unit_of_measurement"] == "°F"

    assert hass.states.get("sensor.ndv049a111_outdoor_temperature").state == "-5.0"
    assert hass.states.get("sensor.ndv049a111_water_flow").state == "9.5"
    assert hass.states.get("sensor.ndv049a111_compressor_speed").state == "5"
    assert hass.states.get("sensor.ndv049a111_fault").state == "none"
    # The AXB energy-monitor package is configured, so power sensors exist.
    assert hass.states.get("sensor.ndv049a111_total_power").state == "2780"
    assert hass.states.get("sensor.ndv049a111_heat_of_extraction").state == "18000"


async def test_binary_sensor_states(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Output flags and pressure switches decode to on/off."""
    assert hass.states.get("binary_sensor.ndv049a111_compressor").state == STATE_ON
    assert hass.states.get("binary_sensor.ndv049a111_blower").state == STATE_ON
    assert hass.states.get("binary_sensor.ndv049a111_lockout").state == STATE_OFF
    # Closed switches are healthy: the "open" problem sensors read off.
    assert (
        hass.states.get("binary_sensor.ndv049a111_low_pressure_switch").state
        == STATE_OFF
    )


async def test_thermostat_reflects_the_device(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Mode, setpoints, fan mode and action decode onto the climate entity."""
    state = hass.states.get(THERMOSTAT)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 72.0
    assert state.attributes[ATTR_TEMPERATURE] == 70.0
    assert state.attributes[ATTR_FAN_MODE] == "continuous"
    # Compressor on without the reversing valve energized -> heating.
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_thermostat_writes_land_in_the_command_registers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Mode and setpoint writes go to the Aurora's write-side registers."""
    unit = mock_connection.unit

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: THERMOSTAT, "hvac_mode": HVACMode.COOL},
        blocking=True,
    )
    assert (await unit.read_holding_registers(12606, 1))[0] == 2  # COOL
    # The command register does not echo into the read register on its own —
    # the device applies it. The entity still reads HEAT, so a plain setpoint
    # goes to the heating command register (745 reads, 12619 writes).
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: THERMOSTAT, ATTR_TEMPERATURE: 68.0},
        blocking=True,
    )
    assert (await unit.read_holding_registers(12619, 1))[0] == 680


async def test_thermostat_rejects_an_out_of_range_setpoint(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The library's setpoint window surfaces as a Home Assistant error."""
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: THERMOSTAT, ATTR_TEMPERATURE: 200.0},
            blocking=True,
        )


async def test_zone_entities_follow_the_iz2_count(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Two reported zones -> two zone entities, and no third."""
    zone1 = hass.states.get("climate.ndv049a111_zone_1")
    assert zone1.state == HVACMode.HEAT
    assert zone1.attributes[ATTR_CURRENT_TEMPERATURE] == 71.0
    assert zone1.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

    zone2 = hass.states.get("climate.ndv049a111_zone_2")
    assert zone2.state == HVACMode.COOL
    assert zone2.attributes[ATTR_HVAC_ACTION] == HVACAction.COOLING

    assert hass.states.get("climate.ndv049a111_zone_3") is None


async def test_zone_setpoint_write_uses_the_strided_register(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Zone 2's setpoint lands at its own strided command register."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: "climate.ndv049a111_zone_2", ATTR_TEMPERATURE: 67.0},
        blocking=True,
    )
    # Zone 2 is cooling, so the target goes to its cooling command register:
    # 21204 base + one 9-register zone stride.
    assert (await mock_connection.unit.read_holding_registers(21204 + 9, 1))[0] == 670


async def test_water_heater_reflects_and_controls_dhw(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """The DHW entity reads the tank and writes enable + setpoint."""
    state = hass.states.get(DHW)
    assert state.state == STATE_ELECTRIC
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 125.0
    assert state.attributes[ATTR_TEMPERATURE] == 130.0

    unit = mock_connection.unit
    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        WH_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: DHW, ATTR_TEMPERATURE: 125.0},
        blocking=True,
    )
    assert (await unit.read_holding_registers(401, 1))[0] == 1250

    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_OPERATION_MODE,
        {ATTR_ENTITY_ID: DHW, ATTR_OPERATION_MODE: STATE_OFF},
        blocking=True,
    )
    assert (await unit.read_holding_registers(400, 1))[0] == 0


async def test_derived_sensors(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Values computed across sub-systems, not read from one register."""
    assert hass.states.get("sensor.ndv049a111_water_delta_t").state == "5.0"
    # Heating: 18000 Btuh out of the ground plus the compressor's own work.
    assert float(
        hass.states.get("sensor.ndv049a111_coefficient_of_performance").state
    ) == pytest.approx(2.898, abs=0.01)


async def test_clear_fault_history_button(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Pressing it writes the controller's magic word."""
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.ndv049a111_clear_fault_history"},
        blocking=True,
    )

    assert mock_connection.unit.holding[47] == 0x5555
