"""Humidification / dehumidification control.

The unit packs the humidifier mode into register 12309 (auto-humidify /
auto-dehumidify flags) and both targets into register 12310 (humidification in
the high byte, dehumidification in the low byte), so each setting is declared as
its own run of bits inside that one register. Register 362 reports whether
active dehumidification is currently running.
"""

from __future__ import annotations

from modbus_connection.model import bit, bits, boolean

from .model import AuroraComponent


class Humidistat(AuroraComponent):
    """Humidification and dehumidification modes and targets."""

    active_dehumidification = boolean(362)
    """Whether dehumidification is running right now."""

    auto_humidification = bit(12309, 15)
    """Whether automatic humidification is enabled."""

    auto_dehumidification = bit(12309, 14)
    """Whether automatic dehumidification is enabled."""

    humidification_target = bits(12310, 8, 8, unit="%")
    """Target relative humidity for humidification (%)."""

    dehumidification_target = bits(12310, 0, 8, unit="%")
    """Target relative humidity for dehumidification (%)."""
