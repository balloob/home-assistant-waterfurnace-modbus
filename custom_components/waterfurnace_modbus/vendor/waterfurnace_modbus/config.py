"""Installed-hardware configuration — how the unit was set up.

These are the registers an integration reads once at startup to discover what the
unit actually has (VS pump vs fixed, energy-monitor package, zone count) and
decide which entities to create.
"""

from __future__ import annotations

from modbus_connection.model import enum, integer

from .enums import (
    BlowerType,
    EnergyMonitorType,
    FlowMeterType,
    PhaseType,
    PumpType,
)
from .model import AuroraComponent, pressure

_ANTIFREEZE_CODE = 485


class Configuration(AuroraComponent):
    """Installed-hardware / setup configuration."""

    number_of_zones = integer(483, signed=False)  # IZ2 zone count (0 = no IZ2)
    blower_type = enum(404, BlowerType)
    pump_type = enum(413, PumpType)
    flow_meter_type = enum(403, FlowMeterType)
    phase = enum(416, PhaseType)
    energy_monitor = enum(412, EnergyMonitorType)
    loop_pressure_trip = pressure(419)
    _brine_raw = integer(402, signed=False)

    @property
    def brine_type(self) -> str | None:
        """Loop fluid: ``"Antifreeze"`` or ``"Water"``."""
        raw = self._brine_raw
        if raw is None:
            return None
        return "Antifreeze" if raw == _ANTIFREEZE_CODE else "Water"
