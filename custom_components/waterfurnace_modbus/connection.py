"""Build the Modbus connection a config entry describes.

The integration owns its connection, per the modbus-connection integration
guide: construction performs no I/O, requests connect on demand, and a dropped
link re-establishes itself on the next poll — the config entry is never
reloaded for a drop. Kept in its own module so tests (and, later, a shared-
connection provider) replace exactly one seam.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from modbus_connection import ModbusSerialParams, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_FRAMER,
    CONF_PARITY,
    CONF_SERIAL_DEVICE,
    CONNECTION_TYPE_SERIAL,
    DEFAULT_BAUDRATE,
    DEFAULT_FRAMER,
    DEFAULT_PARITY,
    DEFAULT_PORT,
)


def build_connection(data: Mapping[str, Any]) -> ModbusConnection:
    """Return the (unconnected) connection for a config entry's data."""
    if data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_SERIAL:
        params: ModbusTcpParams | ModbusSerialParams = ModbusSerialParams(
            device=data[CONF_SERIAL_DEVICE],
            baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
            # Stored lowercase (translation keys must be); params want E/N/O.
            parity=data.get(CONF_PARITY, DEFAULT_PARITY).upper(),
        )
    else:
        params = ModbusTcpParams(
            host=data[CONF_HOST],
            port=data.get(CONF_PORT, DEFAULT_PORT),
            framer=data.get(CONF_FRAMER, DEFAULT_FRAMER),
        )
    return ModbusConnection(params)
