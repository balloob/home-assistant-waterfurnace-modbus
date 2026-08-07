"""Small helpers shared across sub-systems: the fault-code table."""

from __future__ import annotations

# Fault code -> human name, from the upstream map (``registers.rb`` ``FAULTS``).
# The ABC reports the code in register 25; the historical fault buffer (601-699)
# stores the same codes.
FAULTS: dict[int, str] = {
    # ABC / AXB basic faults
    1: "Input Error",
    2: "High Pressure",
    3: "Low Pressure",
    4: "Freeze Detect FP2",
    5: "Freeze Detect FP1",
    7: "Condensate Overflow",
    8: "Over/Under Voltage",
    9: "AirF/RPM",
    10: "Compressor Monitor",
    11: "FP1/2 Sensor Error",
    12: "RefPerfrm Error",
    # miscellaneous
    13: "Non-Critical AXB Sensor Error",
    14: "Critical AXB Sensor Error",
    15: "Hot Water Limit",
    16: "VS Pump Error",
    17: "Communicating Thermostat Error",
    18: "Non-Critical Communications Error",
    19: "Critical Communications Error",
    21: "Low Loop Pressure",
    22: "Communicating ECM Error",
    23: "HA Alarm 1",
    24: "HA Alarm 2",
    25: "AxbEev Error",
    # VS drive (Series 7)
    41: "High Drive Temp",
    42: "High Discharge Temp",
    43: "Low Suction Pressure",
    44: "Low Condensing Pressure",
    45: "High Condensing Pressure",
    46: "Output Power Limit",
    47: "EEV ID Comm Error",
    48: "EEV OD Comm Error",
    49: "Cabinet Temperature Sensor",
    51: "Discharge Temp Sensor",
    52: "Suction Pressure Sensor",
    53: "Condensing Pressure Sensor",
    54: "Low Supply Voltage",
    55: "Out of Envelope",
    56: "Drive Over Current",
    57: "Drive Over/Under Voltage",
    58: "High Drive Temp",
    59: "Internal Drive Error",
    61: "Multiple Safe Mode",
    # EEV2
    71: "Loss of Charge",
    72: "Suction Temperature Sensor",
    73: "Leaving Air Temperature Sensor",
    74: "Maximum Operating Pressure",
    99: "System Reset",
}


def fault_name(code: int | None) -> str | None:
    """Human name for a fault code, or ``None`` when there is no active fault.

    Code ``0`` (and ``None``) means "no fault". An unknown non-zero code is
    returned as ``"E<code>"``.
    """
    if not code:
        return None
    return FAULTS.get(code, f"E{code}")
