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
from modbus_connection import ModbusConnection, ModbusError, ModbusTimeoutError

from .const import DOMAIN, SCAN_INTERVAL
from .vendor.waterfurnace_modbus import Series7, UpdateReport

_LOGGER = logging.getLogger(__name__)

# Consecutive timed-out polls after which the link is treated as stuck —
# a peer that keeps the socket open but stops answering, which cheap
# RTU-over-TCP bridges are prone to — and recycled with disconnect().
_STUCK_LINK_TIMEOUTS = 3

type AuroraConfigEntry = ConfigEntry[AuroraCoordinator]


class AuroraCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Poll the live sub-systems of a Series7, one sub-system at a time.

    Which sub-systems those are is the library's call: ``async_setup()`` has
    already read the registers that describe the installed hardware — identity,
    configuration, board presence, dealer details — so ``async_update()``
    refreshes only what can change between two polls.

    The poll's ``UpdateReport`` is the coordinator's data: a sub-system whose
    block the controller would not answer is listed in ``failed``, and the
    entities reading it go unavailable while the rest keep updating. A poll that
    refreshed nothing at all is the whole heat pump being unreachable, and fails.

    A dropped link is not an entry reload: the connection re-establishes itself
    on the next request, so the next successful poll brings the entities back.
    """

    _failed: frozenset[str] = frozenset()

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AuroraConfigEntry,
        device: Series7,
        connection: ModbusConnection,
    ) -> None:
        """Initialize the coordinator over a device that has been set up."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self._connection = connection
        self._consecutive_timeouts = 0
        # The zones the IZ2 board reported during setup; one entity set each.
        self.zones = device.live_zones

    async def _async_update_data(self) -> UpdateReport:
        """Refresh the polled sub-systems and report what got through.

        A link can go bad without dropping: the peer keeps the socket open
        but stops answering. Since the sub-systems are read separately that
        shows up as a poll where every one of them failed rather than as a
        raised error, and after enough consecutive such polls the link is
        recycled with ``disconnect()`` — not permanent like ``close()`` — so
        the next poll opens a fresh one over the same handles.
        """
        try:
            report = await self.device.async_update()
        except ModbusError as err:  # the link itself; a block never gets here
            raise UpdateFailed(f"Error reading the heat pump: {err}") from err

        if report.failed and not report.updated:
            errors = list(report.failed.values())
            if all(isinstance(err, ModbusTimeoutError) for err in errors):
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
            # Home Assistant logs str(err) at error level and the traceback at
            # debug, so the message names a failure and the chained group keeps
            # the rest reachable.
            raise UpdateFailed(
                f"The heat pump did not respond: {errors[0]}"
            ) from ExceptionGroup("every sub-system failed", errors)

        self._consecutive_timeouts = 0
        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning("Failed to fetch %s: %s", name, report.failed[name])
        self._failed = frozenset(report.failed)
        return report
