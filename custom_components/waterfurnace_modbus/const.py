"""Constants for the WaterFurnace Aurora (Modbus) integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "waterfurnace_modbus"

CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_FRAMER: Final = "framer"
CONF_SERIAL_DEVICE: Final = "serial_device"
CONF_BAUDRATE: Final = "baudrate"
CONF_PARITY: Final = "parity"
CONF_UNIT_ID: Final = "unit_id"

CONNECTION_TYPE_NETWORK: Final = "network"
CONNECTION_TYPE_SERIAL: Final = "serial"

# The Aurora ABC speaks Modbus RTU on RS-485 at 19200 8E1, unit address 1.
# Over a network it is almost always behind a transparent serial
# (RTU-over-TCP) gateway, hence the rtu framer default for TCP.
DEFAULT_PORT: Final = 502
DEFAULT_FRAMER: Final = "rtu"
DEFAULT_BAUDRATE: Final = 19200
DEFAULT_PARITY: Final = "E"
DEFAULT_UNIT_ID: Final = 1

SCAN_INTERVAL: Final = timedelta(seconds=30)
