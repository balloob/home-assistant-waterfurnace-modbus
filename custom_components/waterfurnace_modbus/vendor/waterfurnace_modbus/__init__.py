"""waterfurnace-modbus — read a WaterFurnace 7 Series heat pump over Modbus.

Construct ``Series7(unit)`` with a ``modbus_connection.ModbusUnit``, call
``await device.async_update()``, then read its sub-systems as normal Python
objects::

    device.sensors.entering_water
    device.compressor.speed_actual
    device.thermostat.heating_setpoint
    device.zones[0].mode
    device.status.fault

The library is organized by sub-system — one file each for ``device_info``,
``config``, ``peripherals``, ``status``, ``sensors``, ``compressor``, ``blower``,
``pump``, ``dhw``, ``thermostat``, ``humidistat``, ``energy``, ``dealer`` and the
IZ2 ``zone`` — built on the generic ``Component`` / ``RegisterField`` framework in
``modbus_connection.model``.

The register map follows the reverse-engineered Aurora point list from the
`ccutrer/waterfurnace_aurora <https://github.com/ccutrer/waterfurnace_aurora>`_
project. It is modelled primarily for the variable-speed Series 7 (the ``ABCVSP``
program) but covers the wider ABC/AXB/IZ2 register set.
"""

from .blower import Blower
from .compressor import Compressor
from .config import Configuration
from .dealer import Dealer
from .device_info import DeviceInformation
from .dhw import DHW
from .energy import Energy
from .enums import (
    BlowerType,
    EnergyMonitorType,
    FanMode,
    FlowMeterType,
    HeatingMode,
    PhaseType,
    PumpType,
    SystemOutput,
    SystemStatus,
    VSAlarm,
    VSDriveDerate,
    VSSafeMode,
    ZoneCall,
)
from .humidistat import Humidistat
from .model import UpdateReport
from .peripherals import Peripherals
from .pump import Pump
from .sensors import Sensors
from .series7 import Series7
from .status import Status
from .thermostat import Thermostat
from .utils import FAULTS, fault_name
from .zone import Zone

__all__ = [
    "FAULTS",
    "DHW",
    "Blower",
    "BlowerType",
    "Compressor",
    "Configuration",
    "Dealer",
    "DeviceInformation",
    "Energy",
    "EnergyMonitorType",
    "FanMode",
    "FlowMeterType",
    "HeatingMode",
    "Humidistat",
    "Peripherals",
    "PhaseType",
    "Pump",
    "PumpType",
    "Sensors",
    "Series7",
    "Status",
    "SystemOutput",
    "SystemStatus",
    "Thermostat",
    "UpdateReport",
    "VSAlarm",
    "VSDriveDerate",
    "VSSafeMode",
    "Zone",
    "ZoneCall",
    "fault_name",
]
