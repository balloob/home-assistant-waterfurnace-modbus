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
        pump_heat.live_zones[0].mode                # per-zone climate
        pump_heat.status.fault                      # str | None
        pump_heat.info.model

    Each sub-system can also be refreshed on its own (``await
    pump_heat.compressor.async_update()``) and exposes ``add_update_listener`` so
    a single Home Assistant entity can subscribe to just the part it shows.

    The device sets itself up once — :meth:`async_setup`, run by the first
    :meth:`async_update` if you don't call it yourself — and polls only what can
    change after that. :attr:`info`, :attr:`config`, :attr:`peripherals` and
    :attr:`dealer` describe hardware that cannot change while the unit runs, so
    they are read in setup and not polled again.

    :attr:`zones` always holds six ``Zone`` objects, whatever the unit has;
    :attr:`live_zones` holds the ones the IZ2 board reports (empty without an IZ2
    board) and is what a poll refreshes.
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
        # Both settled by async_setup(), which needs the zone count off the device.
        self.live_zones: tuple[Zone, ...] = ()
        self._group: ComponentGroup | None = None

    @property
    def components(self) -> tuple[Component, ...]:
        """Every sub-system, for iteration — polled or not."""
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

    @property
    def polled_components(self) -> tuple[Component, ...]:
        """The sub-systems a poll refreshes: everything that can change.

        Only the zones are dropped for a unit that does not have them. A board
        the unit lacks — no AXB, no energy monitor — still answers its registers
        with ``0`` rather than refusing them, so leaving :attr:`dhw` and
        :attr:`energy` in costs a few registers and never a failed read.
        """
        return (
            self.status,
            self.sensors,
            self.compressor,
            self.blower,
            self.pump,
            self.dhw,
            self.thermostat,
            self.humidistat,
            self.energy,
            *self.live_zones,
        )

    async def async_setup(self) -> None:
        """Read what cannot change while the unit runs, and settle what to poll.

        Run by the first :meth:`async_update` if the caller does not run it
        itself — worth calling explicitly where "this device is unusable" and
        "this poll failed" are different outcomes, as they are for a Home
        Assistant config entry. A failure leaves the device unset up, so the
        next :meth:`async_update` tries again.
        """
        await ComponentGroup(
            self._unit, [self.info, self.config, self.peripherals, self.dealer]
        ).async_update()
        self.live_zones = self.zones[: self.config.number_of_zones or 0]
        # One pooled-read group over every polled sub-system; it derives the
        # readable ranges from the components and caches its block plan.
        self._group = ComponentGroup(self._unit, self.polled_components)

    async def async_update(self) -> None:
        """Refresh every polled sub-system in as few Modbus calls as possible.

        The first call sets the device up (:meth:`async_setup`). All sub-systems
        share one unit, so their register reads are pooled into a single
        consolidated set of block reads — adjacent registers from different
        sub-systems are fetched together — rather than each component querying
        independently. Listeners then fire per sub-system.
        """
        if self._group is None:
            await self.async_setup()
        assert self._group is not None  # async_setup() always builds it
        await self._group.async_update()
