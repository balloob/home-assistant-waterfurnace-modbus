"""The top-level WaterFurnace device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
    ModbusTimeoutError,
)
from modbus_connection.model import Component, ComponentGroup

from .blower import Blower
from .compressor import Compressor
from .config import Configuration
from .dealer import Dealer
from .device_info import DeviceInformation
from .dhw import DHW
from .energy import Energy
from .enums import SystemOutput
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
# Order matters: the first component read is the poll's probe, so it is status —
# one block of the ABC's own core registers, the cheapest read on the device and
# the one a working controller always answers.
# What moves on its own, and what moves only when something writes it. A
# consumer polls the readings on its own interval and the settings rarely.
_READINGS = (
    "status",
    "sensors",
    "compressor",
    "blower",
    "pump",
    "dhw",
    "energy",
)

_SETTINGS = ("thermostat", "humidistat")

# Btu per watt-hour, for putting electrical input and thermal output in one unit.
_BTU_PER_WATT_HOUR = 3.412

# A COP outside this is a bad register rather than a heat pump.
_COP_PLAUSIBLE = (0.5, 15.0)


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
        self._readings: dict[str, AuroraComponent] | None = None
        self._settings: dict[str, AuroraComponent] = {}

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
    def water_delta_t(self) -> float | None:
        """How much the loop water changed across the coax, in °F.

        Unsigned: the unit takes heat out of the loop in heating and puts it
        back in cooling, and the size is what says how hard it is working.
        """
        leaving = self.sensors.leaving_water
        entering = self.sensors.entering_water
        if leaving is None or entering is None:
            return None
        return abs(leaving - entering)

    @property
    def cop(self) -> float | None:
        """Coefficient of performance: useful heat out over electricity in.

        The Aurora names its heat registers from the ground loop's side, so
        which one carries the useful figure depends on the reversing valve.
        Energy is conserved either way: heating delivers what came out of the
        ground *plus* the compressor's work, cooling removes what went into the
        ground *minus* it.

        0.0 with the compressor off, and None when the unit reports nothing to
        divide, or a figure outside :data:`_COP_PLAUSIBLE` — a reading that far
        out is a bad register, not a heat pump.
        """
        outputs = self.status.outputs
        if outputs is None:
            return None
        if not (SystemOutput.COMPRESSOR_1 | SystemOutput.COMPRESSOR_2) & outputs:
            return 0.0

        watts = self.energy.total_power
        if not watts:
            return None

        cooling = SystemOutput.REVERSING_VALVE in outputs
        ground = (
            self.energy.heat_of_rejection if cooling else self.energy.heat_of_extraction
        )
        if ground is None:
            return None

        work = watts * _BTU_PER_WATT_HOUR
        useful = abs(ground) - work if cooling else abs(ground) + work
        if useful <= 0:
            return None
        value = useful / work
        low, high = _COP_PLAUSIBLE
        return value if low <= value <= high else None

    @property
    def approach_temperature(self) -> float | None:
        """How far the condenser sits above what it is rejecting heat into.

        The condenser is the water coax in cooling and the indoor air coil in
        heating, so the reference changes with the reversing valve. None with
        the compressor off, and in heating on a unit without the AXB board,
        which is what reports supply air.
        """
        outputs = self.status.outputs
        if outputs is None:
            return None
        if not (SystemOutput.COMPRESSOR_1 | SystemOutput.COMPRESSOR_2) & outputs:
            return None

        condenser = self.compressor.saturated_condenser_temperature
        if condenser is None:
            return None

        cooling = SystemOutput.REVERSING_VALVE in outputs
        reference = self.sensors.entering_water if cooling else self.sensors.leaving_air
        if reference is None:
            return None
        return condenser - reference

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

        # Return air sits at a different register with and without the AXB
        # board, which also serves supply air at all.
        self.sensors.has_axb = bool(self.peripherals.has_axb)

        # The poll list doubles as the setup marker: None means "not set up yet".
        self._readings = {name: getattr(self, name) for name in _READINGS}
        self._readings.update(
            (f"zone_{index}", zone)
            for index, zone in enumerate(self.live_zones, start=1)
        )

        # A humidistat the unit cannot act on reports targets nothing honours.
        await self.humidistat.async_update()
        self._settings = {name: getattr(self, name) for name in _SETTINGS}
        if not self._has_humidistat():
            del self._settings["humidistat"]

    def _has_humidistat(self) -> bool:
        """Whether this unit can actually humidify or dehumidify.

        A unit with neither, and no Symphony link to drive them, still answers
        the registers, so the targets would read as settings nothing honours.
        """
        return bool(
            self.humidistat.auto_humidification
            or self.humidistat.auto_dehumidification
            or self.peripherals.has_awl
        )

    async def async_update_readings(self) -> UpdateReport:
        """Refresh what the unit measures and controls on its own."""
        if self._readings is None:
            await self.async_setup()
        assert self._readings is not None  # async_setup() builds it
        return await self._async_poll(self._readings)

    async def async_update_settings(self) -> UpdateReport:
        """Refresh what someone configured: setpoints, modes, humidity targets.

        These move when something writes them, so a consumer polls them on a
        slower interval than the readings, and again after writing one.
        """
        if self._readings is None:
            await self.async_setup()
        return await self._async_poll(self._settings)

    async def async_update(self) -> UpdateReport:
        """Refresh every polled sub-system, one at a time.

        The first call sets the device up (:meth:`async_setup`). Sub-systems are
        read independently: one that fails keeps its previous values while the
        rest still refresh. Listeners fire only after every sub-system has been
        tried, and only for the ones that refreshed. A failure of the link itself
        raises ``ModbusConnectionError`` instead of reporting.

        A timeout before anything has answered raises ``ModbusTimeoutError``
        rather than walking the remaining sub-systems into their own timeouts.
        Containing a timeout is only right once the unit has proven it is there;
        until then a silent unit would cost eleven timeouts instead of one.
        """
        if self._readings is None:
            await self.async_setup()
        assert self._readings is not None  # async_setup() builds it
        return await self._async_poll({**self._readings, **self._settings})

    async def _async_poll(self, polled: dict[str, AuroraComponent]) -> UpdateReport:
        """Read each sub-system on its own, collecting what happened."""
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name, component in polled.items():
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except ModbusTimeoutError as err:
                if not updated and not failed:
                    raise  # nothing has answered yet: the whole unit is silent
                failed[name] = err
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            polled[name].notify()
        return UpdateReport(updated, failed)

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Every register this device reads, undecoded — for diagnostics.

        Covers the setup-only blocks as well as the polled ones, so a dump
        carries the identity and installed-hardware registers an issue report
        needs. Left out are the blocks this unit does not serve: the dealer
        block where it refused those addresses, and the zones past
        :attr:`live_zones`. The first call sets the device up.

        The fields refresh but no listener fires: a dump is not a poll, and a
        consumer's entities should not take a state from a diagnostics download.
        """
        if self._readings is None:
            await self.async_setup()
        assert self._readings is not None  # async_setup() builds it
        group = ComponentGroup(
            self._unit,
            [*self._static, *self._readings.values(), *self._settings.values()],
        )
        return await group.async_read_raw(notify=False)
