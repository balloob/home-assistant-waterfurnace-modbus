"""Setup, teardown and connection-lifecycle tests."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.waterfurnace_modbus.const import DOMAIN, SCAN_INTERVAL
from custom_components.waterfurnace_modbus.vendor.waterfurnace_modbus import Series7

from .conftest import ENTRY_DATA, ConnectionFactory


async def test_setup_creates_the_device(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """One heat pump becomes one device with its Modbus-read identity."""
    assert config_entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device({(DOMAIN, config_entry.entry_id)})
    assert device is not None
    assert device.manufacturer == "WaterFurnace"
    assert device.model == "NDV049A111"
    assert device.serial_number == "1234567890"
    assert device.sw_version == "3.05"


async def test_an_unreadable_heat_pump_retries_setup(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> None:
    """A device that cannot be read is a retried setup, not a loaded empty entry.

    The library's setup read runs from ``async_setup_entry``, so a heat pump
    that does not answer never reaches the coordinator.
    """
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry = MockConfigEntry(domain=DOMAIN, title="NDV049A111", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    with (
        patch.object(
            Series7, "async_setup", side_effect=ModbusTimeoutError("no response")
        ),
        patch.object(Series7, "async_update") as poll,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not poll.called  # the setup read failed before any poll was tried


async def test_unload_closes_the_connection(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """Unloading tears the entry down and permanently closes the connection."""
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert not mock_connection.connections[-1].connected


async def test_a_dropped_link_heals_without_a_reload(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """A drop marks entities unavailable; the next poll reconnects on its own."""
    connection = mock_connection.connections[-1]
    entity_id = "sensor.ndv049a111_entering_water_temperature"
    assert hass.states.get(entity_id).state == "50.0"

    connection.simulate_connection_lost()
    # The link healing is the connection's own doing — the poll reconnects.
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(entity_id).state == "50.0"
    # Only setup's connection was ever built: no reload, no rebuild.
    assert len(mock_connection.connections) == 1


async def test_a_stuck_link_is_recycled_after_repeated_timeouts(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_connection: ConnectionFactory,
) -> None:
    """A peer that answers nothing gets its link recycled, then heals.

    Polls are driven directly — the subject is the coordinator's timeout
    counting and recycle, not Home Assistant's refresh scheduling.
    """
    coordinator = config_entry.runtime_data
    connection = mock_connection.connections[-1]
    unit = mock_connection.unit
    entity_id = "sensor.ndv049a111_entering_water_temperature"
    assert connection.connected

    unit.fail_requests(ModbusTimeoutError("no response"))
    for _ in range(2):
        await coordinator.async_refresh()
    # Two timeouts: unavailable, but the link has not been recycled yet.
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert connection.connected

    await coordinator.async_refresh()
    # The third consecutive timeout tore the link down...
    assert not connection.connected

    # ...and once the peer answers again, the next poll reconnects and heals —
    # same connection, same handles, no reload.
    unit.fail_requests(None)
    await coordinator.async_refresh()
    assert hass.states.get(entity_id).state == "50.0"
    assert len(mock_connection.connections) == 1
