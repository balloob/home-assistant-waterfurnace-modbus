"""Aurora-specific pieces layered on the ``modbus_connection.model`` framework.

The generic ``Component`` base, the field descriptors and the typed factories
come straight from ``modbus_connection.model`` — sub-systems import those
directly. This module adds only what is specific to the WaterFurnace Aurora
control:

- :class:`AuroraComponent`, a ``Component`` preset with the controller's readable
  register ranges and its 100-register read cap;
- :func:`temperature`, a signed 0.1-scaled °F register;
- :func:`pressure`, an unsigned 0.1-scaled psi register.

Everything on this device is a holding register (FC03); there are no coils, so
booleans are packed as bits inside registers — read with :func:`flags` for a
whole bitmask, or :func:`bit` / :func:`bits` for one setting inside a shared word.
"""

from __future__ import annotations

from dataclasses import dataclass

from modbus_connection import ModbusError
from modbus_connection.model import Component, RegisterField, gauge

from .ranges import MAX_READ_SPAN, REGISTER_RANGES


class AuroraComponent(Component):
    """An Aurora sub-system: the controller's readable ranges + its read cap."""

    register_ranges = REGISTER_RANGES
    max_span = MAX_READ_SPAN


@dataclass(frozen=True)
class UpdateReport:
    """What one poll refreshed, by the device's component attribute names.

    Zones are keyed ``zone_<n>`` after their 1-based position in
    :attr:`~waterfurnace_modbus.Series7.live_zones`; every other sub-system by
    its attribute name. A failed component kept its previous values and did not
    notify; the error that failed it rides along. A dead link is never in here —
    the update raises ``ModbusConnectionError`` instead of reporting partial
    silence — and neither is a unit that never answered at all, which raises
    ``ModbusTimeoutError``. A timeout that *is* in here means the unit answered
    something else, so only that block is slow.
    """

    updated: set[str]
    failed: dict[str, ModbusError]

    @property
    def complete(self) -> bool:
        """Whether every polled component refreshed."""
        return not self.failed


def temperature(
    address: int,
    *,
    stride: int = 0,
    writable: bool = False,
) -> RegisterField[float]:
    """A signed 0.1-scaled temperature register (°F)."""
    return gauge(address, 0.1, signed=True, stride=stride, writable=writable, unit="°F")


def pressure(
    address: int,
    *,
    stride: int = 0,
) -> RegisterField[float]:
    """An unsigned 0.1-scaled pressure register (psi)."""
    return gauge(address, 0.1, signed=False, stride=stride, unit="psi")
