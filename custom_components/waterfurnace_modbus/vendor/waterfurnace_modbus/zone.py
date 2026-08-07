"""An IntelliZone 2 (IZ2) zone.

Each zone behaves like its own thermostat. The unit reports up to six; read the
count from :attr:`Configuration.number_of_zones` and use only that many.

Zone data is spread across two strided register blocks: the read side (ambient
temperature and three packed *configuration* words) steps by 3 per zone, while
the write side (mode, setpoints, fan) steps by 9. Each field carries its own
stride, so a ``Zone`` is constructed with a 1-based ``index`` like a heating
circuit. The packed configuration words are decoded exactly as the upstream
``zone_configuration1/2/3`` helpers do — note the heating target's high bit lives
in configuration word 1 and the rest in word 2.
"""

from __future__ import annotations

from modbus_connection.model import enum, raw_register

from .enums import FanMode, HeatingMode, ZoneCall
from .model import AuroraComponent, temperature

# Relative zone size by the 2-bit size code (register 31200 bits 3-4).
_ZONE_SIZES = {0: 0, 1: 25, 2: 45, 3: 70}
_TEMP_BASE = 36  # packed targets are stored as (°F - 36)


class Zone(AuroraComponent):
    """One IZ2 zone. Construct with ``index`` 1-6."""

    ambient_temperature = temperature(31007, stride=3)

    _config1_raw = raw_register(31008, stride=3)  # fan, times, cooling target, carry
    _config2_raw = raw_register(31009, stride=3)  # call, mode, damper, heating target
    _config3_raw = raw_register(31200, stride=3)  # priority, size

    # Write-side registers (a separate strided block).
    _mode_cmd = enum(21202, HeatingMode, stride=9, writable=True)
    _heating_setpoint_cmd = temperature(21203, stride=9, writable=True)
    _cooling_setpoint_cmd = temperature(21204, stride=9, writable=True)
    _fan_mode_cmd = enum(21205, FanMode, stride=9, writable=True)

    @property
    def mode(self) -> HeatingMode | None:
        """Zone operating mode."""
        raw = self._config2_raw
        if raw is None:
            return None
        try:
            return HeatingMode((raw >> 8) & 0x03)
        except ValueError:
            return None

    @property
    def call(self) -> ZoneCall | None:
        """The zone's current heating/cooling call."""
        raw = self._config2_raw
        if raw is None:
            return None
        try:
            return ZoneCall((raw >> 1) & 0x07)
        except ValueError:
            return None

    @property
    def damper_open(self) -> bool | None:
        """Whether the zone's damper is open."""
        raw = self._config2_raw
        return None if raw is None else bool(raw & 0x10)

    @property
    def fan_mode(self) -> FanMode | None:
        """Zone fan mode."""
        raw = self._config1_raw
        if raw is None:
            return None
        if raw & 0x80:
            return FanMode.CONTINUOUS
        if raw & 0x100:
            return FanMode.INTERMITTENT
        return FanMode.AUTO

    @property
    def cooling_target(self) -> int | None:
        """Effective cooling target temperature (°F)."""
        raw = self._config1_raw
        return None if raw is None else ((raw & 0x7E) >> 1) + _TEMP_BASE

    @property
    def heating_target(self) -> int | None:
        """Effective heating target temperature (°F).

        The value's high bit is carried in configuration word 1 and the low five
        bits in word 2, so both reads must be present.
        """
        config1 = self._config1_raw
        config2 = self._config2_raw
        if config1 is None or config2 is None:
            return None
        carry = config1 & 0x01
        return ((carry << 5) | ((config2 & 0xF800) >> 11)) + _TEMP_BASE

    @property
    def economy_priority(self) -> bool | None:
        """Whether the zone runs in economy priority (vs. comfort)."""
        raw = self._config3_raw
        return None if raw is None else bool(raw & 0x20)

    @property
    def size(self) -> int | None:
        """The zone's relative size (0, 25, 45 or 70)."""
        raw = self._config3_raw
        return None if raw is None else _ZONE_SIZES.get((raw >> 3) & 0x03)

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
