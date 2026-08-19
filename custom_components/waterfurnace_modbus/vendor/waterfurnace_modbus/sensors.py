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

    # Return air is at 740 on a unit with the AXB board and at 567 without it,
    # and only the AXB serves supply air at all. async_setup() drops whichever
    # this unit does not have, so the surviving one is what these read.
    _entering_air_axb = temperature(740)
    _entering_air_legacy = temperature(567)
    _leaving_air = temperature(900)
    entering_water = temperature(1111)  # loop water into the unit
    leaving_water = temperature(1110)  # loop water out of the unit
    ambient_air = temperature(502)  # the thermostat's own room sensor
    _outdoor = temperature(742)  # outdoor sensor (communicating stat/AWL)
    relative_humidity = integer(741, signed=False, unit="%")
    air_coil = temperature(20)  # FP2 refrigerant-to-air coil
    cooling_liquid_line = temperature(19)  # FP1 refrigerant liquid line

    @property
    def outdoor(self) -> float | None:
        """Outdoor air temperature, or None when the unit is not AWL-linked.

        The register reads exactly 0 unless the system is AWL-communicating, so
        a unit without Symphony reports a permanent, plausible 0 °F. That costs
        a genuine 0 °F reading, which the upstream Ruby gem and the ESPHome
        component both accept for the same reason.
        """
        return None if self._outdoor == 0 else self._outdoor

    #: Whether the AXB board is installed; ``Series7.async_setup()`` settles it.
    has_axb: bool = True

    @property
    def entering_air(self) -> float | None:
        """Return-air temperature into the unit.

        The AXB board reports it at 740 and a unit without one at 567, so which
        register means anything depends on the hardware.
        """
        return self._entering_air_axb if self.has_axb else self._entering_air_legacy

    @property
    def leaving_air(self) -> float | None:
        """Supply-air temperature out of the unit; None without an AXB board."""
        return self._leaving_air if self.has_axb else None
