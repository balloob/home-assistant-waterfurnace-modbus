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

from modbus_connection.model import Component, RegisterField, gauge

from .ranges import MAX_READ_SPAN, REGISTER_RANGES


class AuroraComponent(Component):
    """An Aurora sub-system: the controller's readable ranges + its read cap."""

    register_ranges = REGISTER_RANGES
    max_span = MAX_READ_SPAN


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
