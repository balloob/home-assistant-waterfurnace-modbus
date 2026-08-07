"""Which control boards are installed, and their firmware versions.

Each peripheral reports a status word (1 active, 2 added, 3 removed, 0xFFFF
missing) followed by a version register (hundredths). An integration reads these
to know which sub-systems to bother polling.
"""

from __future__ import annotations

from modbus_connection.model import gauge, integer

from .model import AuroraComponent

_PRESENT = (1, 2)  # status codes meaning the board is present (active / added)


class Peripherals(AuroraComponent):
    """Presence and firmware version of each Aurora control board."""

    _thermostat_status = integer(800, signed=False)
    thermostat_version = gauge(801, 0.01, signed=False)
    _axb_status = integer(806, signed=False)
    axb_version = gauge(807, 0.01, signed=False)
    _iz2_status = integer(812, signed=False)
    iz2_version = gauge(813, 0.01, signed=False)
    _aoc_status = integer(815, signed=False)
    aoc_version = gauge(816, 0.01, signed=False)
    _moc_status = integer(818, signed=False)
    moc_version = gauge(819, 0.01, signed=False)
    _eev2_status = integer(824, signed=False)
    eev2_version = gauge(825, 0.01, signed=False)
    _awl_status = integer(827, signed=False)
    awl_version = gauge(828, 0.01, signed=False)

    @staticmethod
    def _present(status: int | None) -> bool | None:
        return None if status is None else status in _PRESENT

    @property
    def has_thermostat(self) -> bool | None:
        """Whether a communicating thermostat is installed."""
        return self._present(self._thermostat_status)

    @property
    def has_axb(self) -> bool | None:
        """Whether the AXB expansion board is installed."""
        return self._present(self._axb_status)

    @property
    def has_iz2(self) -> bool | None:
        """Whether the IntelliZone 2 board is installed."""
        return self._present(self._iz2_status)

    @property
    def has_aoc(self) -> bool | None:
        """Whether the AOC (auxiliary output control) board is installed."""
        return self._present(self._aoc_status)

    @property
    def has_moc(self) -> bool | None:
        """Whether the MOC (motor/inverter control) board is installed."""
        return self._present(self._moc_status)

    @property
    def has_eev2(self) -> bool | None:
        """Whether the second electronic-expansion-valve board is installed."""
        return self._present(self._eev2_status)

    @property
    def has_awl(self) -> bool | None:
        """Whether the Aurora Web Link (Symphony) board is installed."""
        return self._present(self._awl_status)
