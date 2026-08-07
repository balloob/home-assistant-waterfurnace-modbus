"""Energy and thermal-power monitoring (AXB energy-monitor option).

These registers are populated only when the unit has the AXB energy-monitor
package; without it they read back as ``0``.
"""

from __future__ import annotations

from modbus_connection.model import int32, uint32

from .model import AuroraComponent


class Energy(AuroraComponent):
    """Per-load electrical power and geothermal heat transfer."""

    compressor_power = uint32(1146, unit="W")
    blower_power = uint32(1148, unit="W")
    aux_power = uint32(1150, unit="W")
    total_power = uint32(1152, unit="W")
    pump_power = uint32(1164, unit="W")
    heat_of_extraction = int32(1154, unit="Btuh")  # heat pulled from the loop
    heat_of_rejection = int32(1156, unit="Btuh")  # heat pushed to the loop
