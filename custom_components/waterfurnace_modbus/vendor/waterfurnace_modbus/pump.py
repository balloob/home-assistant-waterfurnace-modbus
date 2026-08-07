"""The variable-speed loop pump (Series 7 flow center)."""

from __future__ import annotations

from modbus_connection.model import gauge, integer, uint32

from .model import AuroraComponent, pressure

_PUMP_SPEED_RANGE = range(1, 101)  # valid VS pump speed is 1-100 %


class Pump(AuroraComponent):
    """Variable-speed loop pump: output, its min/max limits, flow and loop pressure."""

    output = integer(325, signed=False, unit="%")  # current pump output
    minimum_speed = integer(321, signed=False, writable=True, unit="%")
    maximum_speed = integer(322, signed=False, writable=True, unit="%")
    waterflow = gauge(1117, 0.1, signed=False, unit="gpm")
    loop_pressure = pressure(1119)
    power = uint32(1164, unit="W")  # requires the energy-monitor option

    async def set_minimum_speed(self, percent: int) -> None:
        """Set the minimum pump-speed limit (1-100 %)."""
        if percent not in _PUMP_SPEED_RANGE:
            raise ValueError("pump speed must be between 1 and 100 %")
        await self.write("minimum_speed", percent)

    async def set_maximum_speed(self, percent: int) -> None:
        """Set the maximum pump-speed limit (1-100 %)."""
        if percent not in _PUMP_SPEED_RANGE:
            raise ValueError("pump speed must be between 1 and 100 %")
        await self.write("maximum_speed", percent)
