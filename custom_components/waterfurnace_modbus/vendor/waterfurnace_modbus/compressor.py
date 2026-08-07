"""The compressor — modelled as the Series 7 variable-speed (VS) drive.

The Series 7 uses an inverter-driven variable-speed compressor whose telemetry
lives in the 3000/3300/3500/3900 register blocks (the ``ABCVSP`` program). Speed
is reported as a stage 0-12: ``speed_desired`` is the target, ``speed_actual``
the current stage (they differ during a ramp).
"""

from __future__ import annotations

from modbus_connection.model import flags, gauge, integer, raw_register, uint32

from .enums import VSAlarm, VSDriveDerate, VSSafeMode
from .model import AuroraComponent, pressure, temperature

_INTERNAL_ERROR_BIT = 0x8000  # register 3226 (VS drive alarm 1)


class Compressor(AuroraComponent):
    """Variable-speed compressor drive (Series 7)."""

    speed_desired = integer(3000, signed=False)  # target stage 0-12
    speed_actual = integer(3001, signed=False)  # current stage 0-12
    discharge_pressure = pressure(3322)
    suction_pressure = pressure(3323)
    discharge_temperature = temperature(3325)
    ambient_temperature = temperature(3326)  # drive cabinet ambient
    drive_temperature = temperature(3327)
    entering_water_temperature = temperature(3330)
    inverter_temperature = temperature(3522)
    suction_temperature = temperature(3903)
    saturated_evaporator_temperature = temperature(3905)
    superheat = temperature(3906)
    line_voltage = integer(3331, signed=False, unit="V")
    fan_speed = integer(3524, signed=False, unit="%")
    eev_open = integer(3808, signed=False, unit="%")  # electronic expansion valve
    power = uint32(3422, unit="W")  # drive compressor power

    # Per-stage compressor current from the AXB energy monitor.
    stage_1_amps = gauge(1107, 0.1, signed=False, unit="A")
    stage_2_amps = gauge(1108, 0.1, signed=False, unit="A")

    # Refrigeration subcooling (AXB refrigeration-monitoring option).
    saturated_condenser_temperature = temperature(1134)
    subcool_heating = temperature(1135)
    subcool_cooling = temperature(1136)

    # VS drive fault bitmasks (Series 7 inverter).
    derate = flags(3223, VSDriveDerate)
    safe_mode = flags(3225, VSSafeMode)
    alarm = flags(3227, VSAlarm)
    _alarm1_raw = raw_register(3226)

    @property
    def internal_error(self) -> bool | None:
        """Whether the VS drive reports an internal error (alarm 1)."""
        raw = self._alarm1_raw
        return None if raw is None else bool(raw & _INTERNAL_ERROR_BIT)
