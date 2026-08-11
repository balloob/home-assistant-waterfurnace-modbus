"""An IntelliZone 2 (IZ2) zone.

Each zone behaves like its own thermostat. The unit reports up to six; the ones
it actually has are :attr:`Series7.live_zones`, sized from
:attr:`Configuration.number_of_zones` during setup.

Zone data is spread across two strided register blocks: the read side (ambient
temperature and three packed *configuration* words) steps by 3 per zone, while
the write side (mode, setpoints, fan) steps by 9. Each field carries its own
stride, so a ``Zone`` is constructed with a 1-based ``index`` like a heating
circuit. Every setting in the configuration words is declared as its own run of
bits, matching the upstream ``zone_configuration1/2/3`` helpers — note the
heating target's high bit lives in configuration word 1 and the rest in word 2.
"""

from __future__ import annotations

from modbus_connection.model import bit, bits, enum

from .enums import FanMode, HeatingMode, ZoneCall
from .model import AuroraComponent, temperature

# Relative zone size by the 2-bit size code (register 31200 bits 3-4).
_ZONE_SIZES = {0: 0, 1: 25, 2: 45, 3: 70}
_TEMP_BASE = 36  # packed targets are stored as (°F - 36)


class Zone(AuroraComponent):
    """One IZ2 zone. Construct with ``index`` 1-6."""

    ambient_temperature = temperature(31007, stride=3)

    # Configuration word 1 (31008): fan, times, cooling target, heating carry.
    _fan_continuous = bit(31008, 7, stride=3)
    _fan_intermittent = bit(31008, 8, stride=3)
    _cooling_target_code = bits(31008, 1, 6, stride=3)
    _heating_target_carry = bits(31008, 0, 1, stride=3)

    # Configuration word 2 (31009): call, mode, damper, heating target.
    _call_code = bits(31009, 1, 3, stride=3)
    _mode_code = bits(31009, 8, 2, stride=3)
    _heating_target_low = bits(31009, 11, 5, stride=3)

    damper_open = bit(31009, 4, stride=3)
    """Whether the zone's damper is open."""

    # Configuration word 3 (31200): priority, size.
    _size_code = bits(31200, 3, 2, stride=3)

    economy_priority = bit(31200, 5, stride=3)
    """Whether the zone runs in economy priority (vs. comfort)."""

    # Write-side registers (a separate strided block).
    _mode_cmd = enum(21202, HeatingMode, stride=9, writable=True)
    _heating_setpoint_cmd = temperature(21203, stride=9, writable=True)
    _cooling_setpoint_cmd = temperature(21204, stride=9, writable=True)
    _fan_mode_cmd = enum(21205, FanMode, stride=9, writable=True)

    @property
    def mode(self) -> HeatingMode | None:
        """Zone operating mode."""
        code = self._mode_code
        if code is None:
            return None
        try:
            return HeatingMode(code)
        except ValueError:
            return None

    @property
    def call(self) -> ZoneCall | None:
        """The zone's current heating/cooling call."""
        code = self._call_code
        if code is None:
            return None
        try:
            return ZoneCall(code)
        except ValueError:
            return None

    @property
    def fan_mode(self) -> FanMode | None:
        """Zone fan mode."""
        continuous = self._fan_continuous
        if continuous is None:
            return None  # both bits come from configuration word 1, unread so far
        if continuous:
            return FanMode.CONTINUOUS
        if self._fan_intermittent:
            return FanMode.INTERMITTENT
        return FanMode.AUTO

    @property
    def cooling_target(self) -> int | None:
        """Effective cooling target temperature (°F)."""
        code = self._cooling_target_code
        return None if code is None else code + _TEMP_BASE

    @property
    def heating_target(self) -> int | None:
        """Effective heating target temperature (°F).

        The value's high bit is carried in configuration word 1 and the low five
        bits in word 2, so both reads must be present.
        """
        carry = self._heating_target_carry
        low = self._heating_target_low
        if carry is None or low is None:
            return None
        return ((carry << 5) | low) + _TEMP_BASE

    @property
    def size(self) -> int | None:
        """The zone's relative size (0, 25, 45 or 70)."""
        code = self._size_code
        return None if code is None else _ZONE_SIZES.get(code)

    async def set_mode(self, mode: HeatingMode) -> None:
        """Set the zone operating mode."""
        await self.write("_mode_cmd", mode)

    async def set_fan_mode(self, mode: FanMode) -> None:
        """Set the zone fan mode."""
        await self.write("_fan_mode_cmd", mode)

    async def set_heating_setpoint(self, fahrenheit: float) -> None:
        """Set the zone heating setpoint (40-90 °F)."""
        if not 40 <= fahrenheit <= 90:
            raise ValueError("heating setpoint must be between 40 and 90 °F")
        await self.write("_heating_setpoint_cmd", fahrenheit)

    async def set_cooling_setpoint(self, fahrenheit: float) -> None:
        """Set the zone cooling setpoint (54-99 °F)."""
        if not 54 <= fahrenheit <= 99:
            raise ValueError("cooling setpoint must be between 54 and 99 °F")
        await self.write("_cooling_setpoint_cmd", fahrenheit)
