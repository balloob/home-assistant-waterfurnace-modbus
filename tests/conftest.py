"""Fixtures: the integration over modbus-connection's in-memory mock.

``build_connection`` is the one seam between the integration and a real
transport; patching it to hand back a ``MockModbusConnection`` preloaded with
Aurora-shaped registers runs the whole stack — config flow, setup, coordinator,
entities — against the mock, with no sockets and no heat pump.
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from custom_components.waterfurnace_modbus.const import (  # noqa: E402
    CONF_CONNECTION_TYPE,
    CONF_FRAMER,
    CONF_UNIT_ID,
    CONNECTION_TYPE_NETWORK,
    DOMAIN,
)

UNIT_ID = 1


def _ascii(text: str) -> list[int]:
    """Pack ASCII into 16-bit registers, two chars per register (hi, lo)."""
    if len(text) % 2:
        text += "\0"
    return [(ord(text[i]) << 8) | ord(text[i + 1]) for i in range(0, len(text), 2)]


# Aurora-shaped holding registers; mirrors the device library's own fixture.
HOLDING: dict[int, int | list[int]] = {
    # -- device identity --
    2: 305,  # ABC program version -> 3.05
    88: _ascii("ABCVSP"),  # ABC program (VS drive)
    92: _ascii("NDV049A111"),  # model number
    105: _ascii("1234567890"),  # serial number
    # -- configuration / capabilities --
    483: 2,  # number of IZ2 zones
    404: 1,  # blower type -> ECM_208_230
    413: 3,  # pump type -> VS_PUMP
    412: 2,  # energy monitor -> ENERGY_MONITOR
    # -- peripherals --
    800: 1,  # thermostat active
    806: 1,  # AXB active
    812: 1,  # IZ2 active
    # -- status --
    16: 244,  # line voltage -> 244 V
    25: 0,  # last fault -> none
    30: 0x09,  # outputs: compressor_1 (0x01) + blower (0x08)
    31: 0x191,  # status: y1 + g + lps closed + hps closed
    # -- sensors --
    740: 700,  # entering air -> 70.0
    1111: 500,  # entering water -> 50.0
    1110: 450,  # leaving water -> 45.0
    742: 65486,  # outdoor -> -5.0 (signed)
    741: 45,  # relative humidity -> 45 %
    # -- compressor --
    3000: 6,  # speed desired
    3001: 5,  # speed actual
    3322: 3500,  # discharge pressure -> 350.0 psi
    3323: 1200,  # suction pressure -> 120.0 psi
    3906: 100,  # superheat -> 10.0
    # -- blower / pump --
    344: 7,  # current ECM speed
    340: 4,  # blower-only speed preset
    1117: 95,  # waterflow -> 9.5 gpm
    1119: 550,  # loop pressure -> 55.0 psi
    325: 65,  # pump output -> 65 %
    # -- domestic hot water --
    400: 1,  # DHW enabled
    401: 1300,  # DHW setpoint -> 130.0
    1114: 1250,  # tank temperature -> 125.0
    # -- thermostat --
    502: 720,  # ambient -> 72.0
    745: 700,  # heating setpoint -> 70.0
    746: 750,  # cooling setpoint -> 75.0
    12006: 0x300,  # mode HEAT (3) packed in bits 8-10
    12005: 0x80,  # fan CONTINUOUS bit
    # -- IZ2 zone 1 (mode heat, call h1, heat 70, cool 74) --
    31007: 710,  # ambient -> 71.0
    31008: 0x4D,
    31009: 0x1314,
    # -- IZ2 zone 2 (mode cool, call c1) --
    31010: 680,  # ambient -> 68.0
    31011: 0x48,
    31012: 0xF20A,
    # -- energy --
    1146: [0, 2400],  # compressor power -> 2400 W
    1152: [0, 2780],  # total power -> 2780 W
    1154: [0, 18000],  # heat of extraction -> 18000 Btuh
}

ENTRY_DATA = {
    CONF_CONNECTION_TYPE: CONNECTION_TYPE_NETWORK,
    "host": "192.168.1.50",
    "port": 502,
    CONF_FRAMER: "rtu",
    CONF_UNIT_ID: UNIT_ID,
}


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the custom integration."""


class ConnectionFactory:
    """Build a fresh preloaded mock per ``build_connection`` call.

    ``close()`` is permanent on a connection — the config flow probes and
    closes, then entry setup builds its own — so each call needs its own mock,
    exactly as each call builds its own real connection.
    """

    def __init__(self) -> None:
        """Start with no connections built."""
        self.connections: list[MockModbusConnection] = []

    def __call__(self, data: object) -> MockModbusConnection:
        """Return a new mock connection with Aurora-shaped registers."""
        connection = MockModbusConnection()
        connection.for_unit(UNIT_ID).holding.update(HOLDING)
        self.connections.append(connection)
        return connection

    @property
    def unit(self):  # noqa: ANN201 - MockModbusUnit
        """The unit handle of the most recently built connection."""
        return self.connections[-1].for_unit(UNIT_ID)


@pytest.fixture
def mock_connection() -> Generator[ConnectionFactory]:
    """Patch the connection seam to Aurora-shaped in-memory mocks."""
    factory = ConnectionFactory()
    with patch(
        "custom_components.waterfurnace_modbus.connection.build_connection",
        side_effect=factory,
    ):
        yield factory


@pytest.fixture
async def config_entry(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> MockConfigEntry:
    """A set-up config entry over the mock connection.

    The tests run under US customary units — where these heat pumps live — so
    states carry the same °F values the registers decode to.
    """
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry = MockConfigEntry(domain=DOMAIN, title="NDV049A111", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
