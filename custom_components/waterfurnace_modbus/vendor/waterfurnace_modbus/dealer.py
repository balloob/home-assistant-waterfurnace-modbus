"""Installer/dealer contact details stored in the controller.

Diagnostic only — populated by the dealer during commissioning (via the AWL /
Symphony tools). Empty on units where it was never set.
"""

from __future__ import annotations

from modbus_connection.model import string

from .model import AuroraComponent


class Dealer(AuroraComponent):
    """Dealer contact information."""

    _name = string(31400, 13)
    _phone = string(31413, 8)
    _address_1 = string(31421, 13)
    _address_2 = string(31434, 13)
    _email = string(31447, 13)
    _website = string(31460, 13)

    @property
    def name(self) -> str | None:
        """Dealer name."""
        return self._name or None

    @property
    def phone(self) -> str | None:
        """Dealer phone number."""
        return self._phone or None

    @property
    def address(self) -> str | None:
        """Dealer address (both stored lines joined)."""
        parts = [p for p in (self._address_1, self._address_2) if p]
        return " ".join(parts) or None

    @property
    def email(self) -> str | None:
        """Dealer email address."""
        return self._email or None

    @property
    def website(self) -> str | None:
        """Dealer website."""
        return self._website or None
