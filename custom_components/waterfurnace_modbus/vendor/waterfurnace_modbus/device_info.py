"""Device identity: the controller's model, program and serial number.

Exposes the fields Home Assistant's ``DeviceInfo`` wants (manufacturer, model,
sw_version, serial_number) directly on the component.
"""

from __future__ import annotations

from modbus_connection.model import gauge, string

from .model import AuroraComponent


class DeviceInformation(AuroraComponent):
    """Controller identity, ABC program and firmware version."""

    manufacturer = "WaterFurnace"

    _model = string(92, 12)  # ASCII model number, e.g. "NDV049..."
    _serial = string(105, 5)  # ASCII serial number
    _abc_version_raw = gauge(2, 0.01, signed=False)  # ABC program version
    program = string(88, 4)  # ABC program name, e.g. "ABCVSP" for a VS drive

    @property
    def model(self) -> str:
        """Model number, or a generic fallback when unread."""
        value = self._model
        return value if value else "Aurora"

    @property
    def serial_number(self) -> str | None:
        """Controller serial number."""
        value = self._serial
        return value or None

    @property
    def firmware_version(self) -> str | None:
        """ABC program (firmware) version, e.g. '3.05'."""
        value = self._abc_version_raw
        return f"{value:.2f}" if value is not None else None
