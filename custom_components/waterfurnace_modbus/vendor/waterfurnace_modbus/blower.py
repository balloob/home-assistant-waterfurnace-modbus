"""The ECM variable-speed blower."""

from __future__ import annotations

from modbus_connection.model import gauge, integer, uint32

from .model import AuroraComponent

_ECM_SPEED_RANGE = range(1, 13)  # valid ECM speed stages are 1-12


class Blower(AuroraComponent):
    """ECM blower: the current speed plus its four configurable speed presets."""

    speed = integer(344, signed=False)  # current ECM speed stage 0-12
    blower_only_speed = integer(340, signed=False, writable=True)
    low_compressor_speed = integer(341, signed=False, writable=True)
    high_compressor_speed = integer(342, signed=False, writable=True)
    aux_heat_speed = integer(347, signed=False, writable=True)
    amps = gauge(1105, 0.1, signed=False, unit="A")
    power = uint32(1148, unit="W")  # requires the energy-monitor option

    async def _set_speed(self, field: str, stage: int) -> None:
        if stage not in _ECM_SPEED_RANGE:
            raise ValueError("ECM speed stage must be between 1 and 12")
        await self.write(field, stage)

    async def set_blower_only_speed(self, stage: int) -> None:
        """Set the fan-only (continuous/G call) ECM speed stage (1-12)."""
        await self._set_speed("blower_only_speed", stage)

    async def set_low_compressor_speed(self, stage: int) -> None:
        """Set the ECM speed stage used at low compressor capacity (1-12)."""
        await self._set_speed("low_compressor_speed", stage)

    async def set_high_compressor_speed(self, stage: int) -> None:
        """Set the ECM speed stage used at high compressor capacity (1-12)."""
        await self._set_speed("high_compressor_speed", stage)

    async def set_aux_heat_speed(self, stage: int) -> None:
        """Set the ECM speed stage used during auxiliary heat (1-12)."""
        await self._set_speed("aux_heat_speed", stage)
