"""Diagnostics: the raw register map behind every entity."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusError
from modbus_connection.model import ComponentGroup

from .coordinator import AuroraConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AuroraConfigEntry
) -> dict[str, Any]:
    """Return the live raw registers, keyed by address.

    The dump replays straight into modbus-connection's mock backend
    (``load_raw``), so an attached diagnostics file can back a regression
    test with no hardware.
    """
    coordinator = entry.runtime_data
    # The whole map — including the identity and installed-hardware registers
    # the coordinator reads only once — freshly read at download time.
    group = ComponentGroup(coordinator.unit, coordinator.device.components)
    try:
        registers: dict[str, Any] = await group.async_read_raw()
    except ModbusError as err:
        registers = {"error": str(err)}
    return {
        "config": {
            "zones": coordinator.device.config.number_of_zones,
            "energy_monitor": str(coordinator.device.config.energy_monitor),
            "has_axb": coordinator.device.peripherals.has_axb,
            "has_iz2": coordinator.device.peripherals.has_iz2,
        },
        "registers": registers,
    }
