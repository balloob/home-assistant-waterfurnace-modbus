"""The top-level WaterFurnace device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
)
from modbus_connection.model import Component, ComponentGroup

from .blower import Blower
from .compressor import Compressor
from .config import Configuration
from .dealer import Dealer
from .device_info import DeviceInformation
from .dhw import DHW
from .energy import Energy
from .humidistat import Humidistat
from .model import AuroraComponent, UpdateReport
from .peripherals import Peripherals
from .pump import Pump
from .sensors import Sensors
from .status import Status
from .thermostat import Thermostat
from .zone import Zone

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

MAX_ZONES = 6  # the IZ2 board supports up to six zones

# Every fixed component attribute a poll may refresh, in read order. The live
# zones are appended in async_setup(), keyed by their 1-based position.
_POLLED = (
    "status",
    "sensors",
    "compressor",
    "blower",
    "pump",
    "dhw",
    "thermostat",
    "humidistat",
    "energy",
)


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
        # All settled by async_setup(), which needs the zone count off the device.
        self.live_zones: tuple[Zone, ...] = ()
        self._static: tuple[AuroraComponent, ...] = ()
        self._polled: dict[str, AuroraComponent] | None = None

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

    async def async_setup(self) -> None:
        """Read what cannot change while the unit runs, and settle what to poll.

        Run by the first :meth:`async_update` if the caller does not run it
        itself — worth calling explicitly where "this device is unusable" and
        "this poll failed" are different outcomes, as they are for a Home
        Assistant config entry. A failure leaves the device unset up, so the
        next :meth:`async_update` tries again.

        Identity, configuration and board presence are what the device is; the
        dealer block is commissioning trivia the AWL tools write, so a unit that
        refuses those addresses outright is set up without it rather than never
        set up at all.
        """
        static: list[AuroraComponent] = [self.info, self.config, self.peripherals]
        await ComponentGroup(self._unit, static).async_update()
        try:
            await self.dealer.async_update()
        except (IllegalDataAddressError, IllegalFunctionError):
            pass  # this unit does not serve the block; a transient error still raises
        else:
            static.append(self.dealer)
        self._static = tuple(static)
        self.live_zones = self.zones[: self.config.number_of_zones or 0]
        # The poll list doubles as the setup marker: None means "not set up yet".
        self._polled = {name: getattr(self, name) for name in _POLLED}
        self._polled.update(
            (f"zone_{index}", zone)
            for index, zone in enumerate(self.live_zones, start=1)
        )

    async def async_update(self) -> UpdateReport:
        """Refresh every polled sub-system, one at a time.

        The first call sets the device up (:meth:`async_setup`). Sub-systems are
        read independently: one that fails keeps its previous values while the
        rest still refresh. Listeners fire only after every sub-system has been
        tried, and only for the ones that refreshed. A failure of the link itself
        raises ``ModbusConnectionError`` instead of reporting.
        """
        if self._polled is None:
            await self.async_setup()
        assert self._polled is not None  # async_setup() builds it
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name, component in self._polled.items():
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            self._polled[name].notify()
        return UpdateReport(updated, failed)

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Every register this device reads, undecoded — for diagnostics.

        Covers the setup-only blocks as well as the polled ones, so a dump
        carries the identity and installed-hardware registers an issue report
        needs. Left out are the blocks this unit does not serve: the dealer
        block where it refused those addresses, and the zones past
        :attr:`live_zones`. The first call sets the device up.
        """
        if self._polled is None:
            await self.async_setup()
        assert self._polled is not None  # async_setup() builds it
        group = ComponentGroup(self._unit, [*self._static, *self._polled.values()])
        return await group.async_read_raw()
