"""Enumerations used across the Aurora model.

The codes match the upstream reverse-engineered map (``registers.rb``): the
mode/fan tables, the system bitmasks, the configuration lookups and the
variable-speed drive fault bitmasks.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag


class HeatingMode(IntEnum):
    """Thermostat / zone operating mode (register 12006 read / 12606 write)."""

    OFF = 0
    AUTO = 1
    COOL = 2
    HEAT = 3
    EHEAT = 4  # emergency (electric-only) heat


class FanMode(IntEnum):
    """Thermostat / zone fan mode (register 12005 read / 12621 write)."""

    AUTO = 0
    CONTINUOUS = 1
    INTERMITTENT = 2


class ZoneCall(IntEnum):
    """An IZ2 zone's current heating/cooling call (register 31009 bits 1-3)."""

    STANDBY = 0
    HEAT_1 = 2
    HEAT_2 = 3
    HEAT_3 = 4
    COOL_1 = 5
    COOL_2 = 6


class BlowerType(IntEnum):
    """Installed blower type (register 404)."""

    PSC = 0
    ECM_208_230 = 1
    ECM_265_277 = 2
    FIVE_SPEED_ECM_460 = 3


class PumpType(IntEnum):
    """Installed loop-pump type (register 413)."""

    OPEN_LOOP = 0
    FC1 = 1
    FC2 = 2
    VS_PUMP = 3
    VS_PUMP_26_99 = 4
    VS_PUMP_UPS26_99 = 5
    FC1_GLNP = 6
    FC2_GLNP = 7


class FlowMeterType(IntEnum):
    """Installed flow-meter type (register 403)."""

    NONE = 0
    THREE_QUARTER_INCH = 1
    ONE_INCH = 2


class PhaseType(IntEnum):
    """Electrical service phase (register 416)."""

    SINGLE = 0
    THREE = 1


class EnergyMonitorType(IntEnum):
    """Installed energy-monitoring package (register 412)."""

    NONE = 0
    COMPRESSOR_MONITOR = 1
    ENERGY_MONITOR = 2


class SystemOutput(IntFlag):
    """The controller's active outputs (register 30)."""

    COMPRESSOR_1 = 0x01  # compressor stage 1
    COMPRESSOR_2 = 0x02  # compressor stage 2
    REVERSING_VALVE = 0x04  # energized = cooling
    BLOWER = 0x08
    AUX_HEAT_1 = 0x10  # electric heat stage 1
    AUX_HEAT_2 = 0x20  # electric heat stage 2
    ACCESSORY = 0x200
    LOCKOUT = 0x400
    ALARM = 0x800


class SystemStatus(IntFlag):
    """The controller's status inputs and pressure switches (register 31).

    The two pressure-switch bits read as *set when the switch is closed* (the
    normal, healthy state).
    """

    Y1 = 0x01  # first-stage call
    Y2 = 0x02  # second-stage call
    W = 0x04  # aux-heat call
    O = 0x08  # reversing-valve call (cooling)  # noqa: E741
    G = 0x10  # fan call
    DEHUMIDIFY_REHEAT = 0x20
    EMERGENCY_SHUTDOWN = 0x40
    LOW_PRESSURE_SWITCH_CLOSED = 0x80
    HIGH_PRESSURE_SWITCH_CLOSED = 0x100
    LOAD_SHED = 0x200


class VSDriveDerate(IntFlag):
    """Variable-speed drive derate reasons (register 3223)."""

    DRIVE_OVER_TEMP = 0x01
    LOW_SUCTION_PRESSURE = 0x04
    LOW_DISCHARGE_PRESSURE = 0x10
    HIGH_DISCHARGE_PRESSURE = 0x20
    OUTPUT_POWER_LIMIT = 0x40


class VSSafeMode(IntFlag):
    """Variable-speed drive safe-mode reasons (register 3225)."""

    EEV_INDOOR_FAILED = 0x01
    EEV_OUTDOOR_FAILED = 0x02
    INVALID_AMBIENT_TEMP = 0x04


class VSAlarm(IntFlag):
    """Variable-speed drive alarms (register 3227)."""

    MULTI_SAFE_MODES = 0x0001
    OUT_OF_ENVELOPE = 0x0002
    OVER_CURRENT = 0x0004
    OVER_VOLTAGE = 0x0008
    DRIVE_OVER_TEMP = 0x0010
    UNDER_VOLTAGE = 0x0020
    HIGH_DISCHARGE_TEMP = 0x0040
    INVALID_DISCHARGE_TEMP = 0x0080
    OEM_COMMUNICATIONS_TIMEOUT = 0x0100
    MOC_SAFETY = 0x0200
    DC_UNDER_VOLTAGE = 0x0400
    INVALID_SUCTION_PRESSURE = 0x0800
    INVALID_DISCHARGE_PRESSURE = 0x1000
    LOW_DISCHARGE_PRESSURE = 0x2000
