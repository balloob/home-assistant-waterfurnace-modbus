"""DataUpdateCoordinator polling the Aurora's live registers."""

from __future__ import annotations

import contextlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import (
    ModbusConnection,
    ModbusError,
    ModbusTimeoutError,
    ModbusUnit,
)
from modbus_connection.model import ComponentGroup

from .const import DOMAIN, SCAN_INTERVAL
from .vendor.waterfurnace_modbus import Series7

_LOGGER = logging.getLogger(__name__)

# Consecutive timed-out polls after which the link is treated as stuck —
# a peer that keeps the socket open but stops answering, which cheap
# RTU-over-TCP bridges are prone to — and recycled with disconnect().
_STUCK_LINK_TIMEOUTS = 3

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
        connection: ModbusConnection,
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
        self._connection = connection
        self._consecutive_timeouts = 0
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
        """Refresh every polled sub-system in a pooled block read.

        A link can go bad without dropping: the peer keeps the socket open
        but stops answering. After enough consecutive timeouts the link is
        recycled with ``disconnect()`` — not permanent like ``close()`` — so
        the next poll opens a fresh one over the same handles.
        """
        try:
            await self._group.async_update()
        except ModbusTimeoutError as err:
            self._consecutive_timeouts += 1
            if self._consecutive_timeouts >= _STUCK_LINK_TIMEOUTS:
                _LOGGER.warning(
                    "No response in %s consecutive polls; recycling the connection",
                    self._consecutive_timeouts,
                )
                self._consecutive_timeouts = 0
                # The link is dropped even when the teardown itself errors.
                with contextlib.suppress(ModbusError):
                    await self._connection.disconnect()
            raise UpdateFailed(f"The heat pump did not respond: {err}") from err
        except ModbusError as err:
            raise UpdateFailed(f"Error reading the heat pump: {err}") from err
        self._consecutive_timeouts = 0
