"""Device-wide temperature and humidity inputs.

Per-subsystem sensors live on their component (compressor refrigerant temps on
:class:`~waterfurnace_modbus.compressor.Compressor`, water flow on
:class:`~waterfurnace_modbus.pump.Pump`, tank temp on
:class:`~waterfurnace_modbus.dhw.DHW`). Only the genuinely device-wide air/water
inputs remain here.

Most of these come from the AXB expansion board; on a unit without one they read
back as ``0``.
"""

from __future__ import annotations

from modbus_connection.model import integer

from .model import AuroraComponent, temperature


class Sensors(AuroraComponent):
    """Controller-wide air and water temperature inputs."""

    entering_air = temperature(740)  # return-air temperature into the unit
    leaving_air = temperature(900)  # supply-air temperature out of the unit
    entering_water = temperature(1111)  # loop water into the unit
    leaving_water = temperature(1110)  # loop water out of the unit
    outdoor = temperature(742)  # outdoor sensor (communicating stat/AWL)
    relative_humidity = integer(741, signed=False, unit="%")
    air_coil = temperature(20)  # FP2 refrigerant-to-air coil
    cooling_liquid_line = temperature(19)  # FP1 refrigerant liquid line
