"""The top-level WaterFurnace device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import Component, ComponentGroup

from .blower import Blower
from .compressor import Compressor
from .config import Configuration
from .dealer import Dealer
from .device_info import DeviceInformation
from .dhw import DHW
from .energy import Energy
from .humidistat import Humidistat
from .peripherals import Peripherals
from .pump import Pump
from .sensors import Sensors
from .status import Status
from .thermostat import Thermostat
from .zone import Zone

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

MAX_ZONES = 6  # the IZ2 board supports up to six zones


class Series7:
    """A WaterFurnace 7 Series Aurora heat pump reached through a ``ModbusUnit``.

    Modelled for the variable-speed 7 Series, using the Aurora ABC/AXB/IZ2/VS-drive
    register set. The device is a tree of independently-updatable sub-systems::

        pump_heat = Series7(unit)
        await pump_heat.async_update()
        pump_heat.sensors.entering_water           # °F
        pump_heat.compressor.speed_actual          # stage 0-12
        pump_heat.thermostat.heating_setpoint      # °F
        pump_heat.zones[0].mode                     # per-zone climate
        pump_heat.status.fault                      # str | None
        pump_heat.info.model

    Each sub-system can also be refreshed on its own (``await
    pump_heat.compressor.async_update()``) and exposes ``add_update_listener`` so
    a single Home Assistant entity can subscribe to just the part it shows. An
    integration typically reads :attr:`config` and :attr:`peripherals` once to
    discover the hardware, then polls only the components it surfaces — rather
    than calling :meth:`async_update`, which refreshes everything.

    :attr:`zones` always holds six ``Zone`` objects; read
    ``config.number_of_zones`` to know how many are real.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        self._unit = unit
        self.info = DeviceInformation(unit)
        self.config = Configuration(unit)
        self.peripherals = Peripherals(unit)
        self.status = Status(unit)
        self.sensors = Sensors(unit)
        self.compressor = Compressor(unit)
        self.blower = Blower(unit)
        self.pump = Pump(unit)
        self.dhw = DHW(unit)
        self.thermostat = Thermostat(unit)
        self.humidistat = Humidistat(unit)
        self.energy = Energy(unit)
        self.dealer = Dealer(unit)
        self.zones = tuple(Zone(unit, index=i) for i in range(1, MAX_ZONES + 1))
        # One pooled-read group over every sub-system; it derives the readable
        # ranges from the components and caches its block plan after the first poll.
        self._group = ComponentGroup(unit, self.components)

    @property
    def components(self) -> tuple[Component, ...]:
        """Every sub-system, for iteration."""
        return (
            self.info,
            self.config,
            self.peripherals,
            self.status,
            self.sensors,
            self.compressor,
            self.blower,
            self.pump,
            self.dhw,
            self.thermostat,
            self.humidistat,
            self.energy,
            self.dealer,
            *self.zones,
        )

    async def async_update(self) -> None:
        """Refresh every sub-system in as few Modbus calls as possible.

        All sub-systems share one unit, so their register reads are pooled into a
        single consolidated set of block reads — adjacent registers from different
        sub-systems are fetched together — rather than each component querying
        independently. Listeners then fire per sub-system.
        """
        await self._group.async_update()
