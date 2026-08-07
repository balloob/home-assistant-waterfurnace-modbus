"""Humidification / dehumidification control.

The unit packs the humidifier mode into register 12309 (auto-humidify /
auto-dehumidify flags) and both targets into register 12310 (humidification in
the high byte, dehumidification in the low byte). Register 362 reports whether
active dehumidification is currently running.
"""

from __future__ import annotations

from modbus_connection.model import boolean, raw_register

from .model import AuroraComponent

_AUTO_DEHUMIDIFY = 0x4000
_AUTO_HUMIDIFY = 0x8000


class Humidistat(AuroraComponent):
    """Humidification and dehumidification modes and targets."""

    active_dehumidification = boolean(362)
    """Whether dehumidification is running right now."""

    _mode_raw = raw_register(12309)
    _targets_raw = raw_register(12310)

    @property
    def auto_humidification(self) -> bool | None:
        """Whether automatic humidification is enabled."""
        raw = self._mode_raw
        return None if raw is None else bool(raw & _AUTO_HUMIDIFY)

    @property
    def auto_dehumidification(self) -> bool | None:
        """Whether automatic dehumidification is enabled."""
        raw = self._mode_raw
        return None if raw is None else bool(raw & _AUTO_DEHUMIDIFY)

    @property
    def humidification_target(self) -> int | None:
        """Target relative humidity for humidification (%)."""
        raw = self._targets_raw
        return None if raw is None else raw >> 8

    @property
    def dehumidification_target(self) -> int | None:
        """Target relative humidity for dehumidification (%)."""
        raw = self._targets_raw
        return None if raw is None else raw & 0xFF
