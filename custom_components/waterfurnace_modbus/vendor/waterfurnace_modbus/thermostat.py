"""The (communicating) thermostat: setpoints, mode and fan mode.

The Aurora reads a setpoint or mode from one register but *writes* it to a
different one — e.g. the heating setpoint reads at 745 and writes at 12619. The
read side is a normal field; each write side is a private writable field the
setter methods drive. Mode and fan mode are bit-packed on read (registers 12006
and 12005) and written as a plain code (12606 and 12621).
"""

from __future__ import annotations

from modbus_connection.model import bit, bits, enum

from .enums import FanMode, HeatingMode
from .model import AuroraComponent, temperature


class Thermostat(AuroraComponent):
    """Communicating-thermostat setpoints, operating mode and fan mode."""

    ambient_temperature = temperature(502)
    heating_setpoint = temperature(745)  # read; written via 12619
    cooling_setpoint = temperature(746)  # read; written via 12620

    _mode_code = bits(12006, 8, 3)
    _fan_continuous = bit(12005, 7)
    _fan_intermittent = bit(12005, 8)

    # Write-side registers (distinct from the read addresses above).
    _heating_setpoint_cmd = temperature(12619, writable=True)
    _cooling_setpoint_cmd = temperature(12620, writable=True)
    _mode_cmd = enum(12606, HeatingMode, writable=True)
    _fan_mode_cmd = enum(12621, FanMode, writable=True)

    @property
    def mode(self) -> HeatingMode | None:
        """Operating mode (off / auto / cool / heat / eheat)."""
        code = self._mode_code
        if code is None:
            return None
        try:
            return HeatingMode(code)
        except ValueError:
            return None

    @property
    def fan_mode(self) -> FanMode | None:
        """Fan mode (auto / continuous / intermittent)."""
        continuous = self._fan_continuous
        if continuous is None:
            return None  # both bits come from register 12005, unread so far
        if continuous:
            return FanMode.CONTINUOUS
        if self._fan_intermittent:
            return FanMode.INTERMITTENT
        return FanMode.AUTO

    async def set_heating_setpoint(self, fahrenheit: float) -> None:
        """Set the heating setpoint (40-90 °F)."""
        if not 40 <= fahrenheit <= 90:
            raise ValueError("heating setpoint must be between 40 and 90 °F")
        await self.write("_heating_setpoint_cmd", fahrenheit)

    async def set_cooling_setpoint(self, fahrenheit: float) -> None:
        """Set the cooling setpoint (54-99 °F)."""
        if not 54 <= fahrenheit <= 99:
            raise ValueError("cooling setpoint must be between 54 and 99 °F")
        await self.write("_cooling_setpoint_cmd", fahrenheit)

    async def set_mode(self, mode: HeatingMode) -> None:
        """Set the operating mode."""
        await self.write("_mode_cmd", mode)

    async def set_fan_mode(self, mode: FanMode) -> None:
        """Set the fan mode."""
        await self.write("_fan_mode_cmd", mode)
