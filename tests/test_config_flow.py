"""Config-flow tests: menu, probe, unique id, failure."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import GatewayTargetError, ModbusConnectionError

from custom_components.waterfurnace_modbus.const import (
    CONF_CONNECTION_TYPE,
    CONF_FRAMER,
    CONF_UNIT_ID,
    CONNECTION_TYPE_NETWORK,
    DOMAIN,
)

from .conftest import ConnectionFactory

NETWORK_INPUT = {
    "host": "192.168.1.50",
    "port": 502,
    CONF_FRAMER: "rtu",
    CONF_UNIT_ID: 1,
}


async def test_network_flow_probes_and_creates_the_entry(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> None:
    """The happy path: menu -> network form -> probed entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": CONNECTION_TYPE_NETWORK}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], NETWORK_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "NDV049A111"  # the probed model number
    assert result["result"].unique_id == "1234567890"  # the probed serial
    assert result["data"] == {
        CONF_CONNECTION_TYPE: CONNECTION_TYPE_NETWORK,
        **NETWORK_INPUT,
    }
    # The probe's connection was closed; setup then built its own.
    assert not mock_connection.connections[0].connected


async def test_network_flow_reports_an_unreachable_device(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> None:
    """A probe failure keeps the form open with a cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": CONNECTION_TYPE_NETWORK}
    )

    with patch(
        "custom_components.waterfurnace_modbus.config_flow._async_probe",
        side_effect=ModbusConnectionError("unreachable"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], NETWORK_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # Fixing the problem lets the same flow finish.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], NETWORK_INPUT
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_a_silent_device_behind_a_live_gateway_is_its_own_error(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> None:
    """A gateway exception (code 11) points at the unit address, not the host."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": CONNECTION_TYPE_NETWORK}
    )

    with patch(
        "custom_components.waterfurnace_modbus.config_flow._async_probe",
        side_effect=GatewayTargetError(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], NETWORK_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "device_not_responding"}


async def test_the_same_heat_pump_cannot_be_added_twice(
    hass: HomeAssistant, mock_connection: ConnectionFactory
) -> None:
    """The probed serial number is the unique id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": CONNECTION_TYPE_NETWORK}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], NETWORK_INPUT
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": CONNECTION_TYPE_NETWORK}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], NETWORK_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
