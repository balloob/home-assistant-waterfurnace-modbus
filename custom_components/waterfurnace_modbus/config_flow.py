"""Config flow for the WaterFurnace Aurora (Modbus) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from modbus_connection import ModbusError

from . import connection as connection_module
from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_FRAMER,
    CONF_PARITY,
    CONF_SERIAL_DEVICE,
    CONF_UNIT_ID,
    CONNECTION_TYPE_NETWORK,
    CONNECTION_TYPE_SERIAL,
    DEFAULT_BAUDRATE,
    DEFAULT_FRAMER,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from .vendor.waterfurnace_modbus import Series7

_UNIT_ID = NumberSelector(
    NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
)
_PORT = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
)
_FRAMER = SelectSelector(
    SelectSelectorConfig(
        options=["rtu", "socket"],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="framer",
    )
)
_BAUDRATE = SelectSelector(
    SelectSelectorConfig(
        options=["9600", "19200", "38400", "57600", "115200"],
        mode=SelectSelectorMode.DROPDOWN,
    )
)
_PARITY = SelectSelector(
    SelectSelectorConfig(
        options=["e", "n", "o"],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="parity",
    )
)

STEP_NETWORK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): _PORT,
        vol.Required(CONF_FRAMER, default=DEFAULT_FRAMER): _FRAMER,
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT_ID,
    }
)

STEP_SERIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_DEVICE): TextSelector(),
        vol.Required(CONF_BAUDRATE, default=str(DEFAULT_BAUDRATE)): _BAUDRATE,
        vol.Required(CONF_PARITY, default=DEFAULT_PARITY): _PARITY,
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT_ID,
    }
)


async def _async_probe(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[str | None, str]:
    """Read the device identity; return (serial number, title).

    Raises ``ModbusError`` when the heat pump cannot be reached.
    """
    connection = connection_module.build_connection(data)
    try:
        device = Series7(connection.for_unit(data[CONF_UNIT_ID]))
        # Only the identity registers: the first read establishes the link.
        await device.info.async_update()
        return device.info.serial_number, device.info.model
    finally:
        await connection.close()


class AuroraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup flow: pick a transport, describe it, probe."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick how the Aurora is reached."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[CONNECTION_TYPE_NETWORK, CONNECTION_TYPE_SERIAL],
        )

    async def async_step_network(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an RTU-over-TCP gateway or native Modbus TCP."""
        return await self._async_step_transport(
            CONNECTION_TYPE_NETWORK, STEP_NETWORK_SCHEMA, user_input
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a directly attached RS-485 line."""
        return await self._async_step_transport(
            CONNECTION_TYPE_SERIAL, STEP_SERIAL_SCHEMA, user_input
        )

    async def _async_step_transport(
        self,
        connection_type: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate the transport details by reading the device identity."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_CONNECTION_TYPE: connection_type,
                **user_input,
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }
            if CONF_PORT in data:
                data[CONF_PORT] = int(data[CONF_PORT])
            if CONF_BAUDRATE in data:
                data[CONF_BAUDRATE] = int(data[CONF_BAUDRATE])
            try:
                serial_number, title = await _async_probe(self.hass, data)
            except ModbusError:
                errors["base"] = "cannot_connect"
            else:
                if serial_number:
                    await self.async_set_unique_id(serial_number)
                    self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id=connection_type,
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
