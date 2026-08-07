"""DataUpdateCoordinator polling the Aurora's live registers."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import ModbusError, ModbusUnit
from modbus_connection.model import ComponentGroup

from .const import DOMAIN, SCAN_INTERVAL
from .vendor.waterfurnace_modbus import Series7

_LOGGER = logging.getLogger(__name__)

type AuroraConfigEntry = ConfigEntry[AuroraCoordinator]


class AuroraCoordinator(DataUpdateCoordinator[None]):
    """Poll the live sub-systems of a Series7 in one pooled read.

    ``config``, ``peripherals`` and ``info`` are read once during setup — they
    describe the installed hardware and never change while the unit runs — so
    each poll covers only the sub-systems entities actually display: status,
    sensors, compressor, blower, pump, DHW, thermostat, humidistat, energy,
    and the zones the IZ2 board reports.

    A dropped link is not an entry reload: the connection re-establishes
    itself on the next request, so a failed poll marks the entities
    unavailable and the next successful one brings them back.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AuroraConfigEntry,
        device: Series7,
        unit: ModbusUnit,
    ) -> None:
        """Initialize the coordinator over the polled component group."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self.unit = unit
        zone_count = device.config.number_of_zones or 0
        self.zones = device.zones[:zone_count]
        self._group = ComponentGroup(
            unit,
            [
                device.status,
                device.sensors,
                device.compressor,
                device.blower,
                device.pump,
                device.dhw,
                device.thermostat,
                device.humidistat,
                device.energy,
                *self.zones,
            ],
        )

    async def _async_update_data(self) -> None:
        """Refresh every polled sub-system in a pooled block read."""
        try:
            await self._group.async_update()
        except ModbusError as err:
            raise UpdateFailed(f"Error reading the heat pump: {err}") from err
