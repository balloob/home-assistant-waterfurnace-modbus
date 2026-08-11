"""Overall controller state: active outputs, status inputs, faults, line voltage."""

from __future__ import annotations

from modbus_connection.model import bit, bits, flags, integer

from .enums import SystemOutput, SystemStatus
from .model import AuroraComponent
from .utils import fault_name


class Status(AuroraComponent):
    """Controller-wide status: what's running, the input calls, and faults."""

    outputs = flags(30, SystemOutput)  # compressor / blower / aux / lockout / alarm
    inputs = flags(31, SystemStatus)  # thermostat calls + pressure switches
    line_voltage = integer(16, signed=False, unit="V")
    line_voltage_setting = integer(112, signed=False, writable=True, unit="V")

    # Registers 25 (last fault) and 26 (last lockout) both carry a fault code in
    # bits 0-14 and a "locked out" flag in bit 15.
    locked_out = bit(25, 15)
    """Whether the controller is locked out on the last fault."""

    _fault_code = bits(25, 0, 15)
    _lockout_latched = bit(26, 15)
    _lockout_code = bits(26, 0, 15)

    @property
    def aux_heat_stage(self) -> int | None:
        """Active auxiliary (electric) heat stage: 0, 1 or 2."""
        outputs = self.outputs
        if outputs is None:
            return None
        if SystemOutput.AUX_HEAT_2 in outputs:
            return 2
        if SystemOutput.AUX_HEAT_1 in outputs:
            return 1
        return 0

    @property
    def last_lockout(self) -> str | None:
        """The fault that last caused a lockout, or ``None`` if never locked out.

        Register 26 carries the code only while its high bit is set.
        """
        if not self._lockout_latched:
            return None
        return fault_name(self._lockout_code)

    @property
    def fault_code(self) -> int | None:
        """The last fault code, or ``None`` when there is no fault."""
        return self._fault_code or None

    @property
    def fault(self) -> str | None:
        """The last fault as a human name, or ``None`` when there is no fault."""
        return fault_name(self.fault_code)

    def _input(self, flag: SystemStatus) -> bool | None:
        inputs = self.inputs
        return None if inputs is None else flag in inputs

    @property
    def low_pressure_switch_closed(self) -> bool | None:
        """Low-pressure switch closed (the healthy state)."""
        return self._input(SystemStatus.LOW_PRESSURE_SWITCH_CLOSED)

    @property
    def high_pressure_switch_closed(self) -> bool | None:
        """High-pressure switch closed (the healthy state)."""
        return self._input(SystemStatus.HIGH_PRESSURE_SWITCH_CLOSED)

    @property
    def emergency_shutdown(self) -> bool | None:
        """Whether the emergency-shutdown input is active."""
        return self._input(SystemStatus.EMERGENCY_SHUTDOWN)

    @property
    def load_shed(self) -> bool | None:
        """Whether a utility load-shed input is active."""
        return self._input(SystemStatus.LOAD_SHED)

    async def set_line_voltage_setting(self, volts: int) -> None:
        """Set the nominal line-voltage setting (90-635 V)."""
        if not 90 <= volts <= 635:
            raise ValueError("line voltage setting must be between 90 and 635 V")
        await self.write("line_voltage_setting", volts)
