"""The WaterFurnace Aurora (Modbus) integration.

Talks Modbus to the Aurora ABC through the vendored ``waterfurnace_modbus``
device library over ``modbus-connection``. The integration owns the
connection; the library only ever sees a ``ModbusUnit``.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from modbus_connection import ModbusError

from . import connection as connection_module
from .const import CONF_UNIT_ID, DEFAULT_UNIT_ID
from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .vendor.waterfurnace_modbus import Series7

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.WATER_HEATER,
]


async def async_setup_entry(hass: HomeAssistant, entry: AuroraConfigEntry) -> bool:
    """Set up a WaterFurnace Aurora from a config entry."""
    connection = connection_module.build_connection(entry.data)
    # The whole teardown; also runs when setup fails below. close() is
    # permanent, so a reload builds a fresh connection.
    entry.async_on_unload(connection.close)

    unit = connection.for_unit(entry.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))
    device = Series7(unit)

    # The library's setup read: identity plus the installed-hardware registers
    # that decide which entities exist (zone count, energy monitor, DHW). Doing
    # it here rather than leaving it to the first poll is what makes an
    # unreadable heat pump a retried setup instead of a loaded, empty entry.
    try:
        await device.async_setup()
    except ModbusError as err:
        raise ConfigEntryNotReady(f"Could not read the heat pump: {err}") from err

    coordinator = AuroraCoordinator(hass, entry, device, connection, unit)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AuroraConfigEntry) -> bool:
    """Unload a WaterFurnace Aurora config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
