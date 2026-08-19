"""Buttons: commands the controller acts on and keeps no state for."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from modbus_connection import ModbusError

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity

CLEAR_FAULT_HISTORY = ButtonEntityDescription(
    key="clear_fault_history",
    translation_key="clear_fault_history",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the controller's command buttons."""
    async_add_entities([AuroraClearFaultHistory(entry.runtime_data.readings)])


class AuroraClearFaultHistory(AuroraEntity, ButtonEntity):
    """Wipe the controller's stored fault history."""

    entity_description = CLEAR_FAULT_HISTORY

    def __init__(self, coordinator: AuroraCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, CLEAR_FAULT_HISTORY.key, components=("status",))

    async def async_press(self) -> None:
        """Clear the fault history on the controller."""
        try:
            await self.coordinator.device.status.async_clear_fault_history()
        except ModbusError as err:
            raise HomeAssistantError(
                f"Could not clear the fault history: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
