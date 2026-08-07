"""Water heater: the AXB domestic-hot-water assist."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the DHW entity when the unit has an AXB board."""
    coordinator = entry.runtime_data
    if coordinator.device.peripherals.has_axb:
        async_add_entities([AuroraWaterHeater(coordinator)])


class AuroraWaterHeater(AuroraEntity, WaterHeaterEntity):
    """Domestic hot water generation: enable and tank setpoint."""

    _attr_translation_key = "dhw"
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.ON_OFF
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_operation_list = [STATE_ELECTRIC, STATE_OFF]
    # The Aurora DHW setpoint window.
    _attr_min_temp = 100.0
    _attr_max_temp = 140.0

    def __init__(self, coordinator: AuroraCoordinator) -> None:
        """Initialize the DHW entity."""
        super().__init__(coordinator, "dhw")

    @property
    def current_temperature(self) -> float | None:
        """The DHW tank temperature."""
        return self.device.dhw.water_temperature

    @property
    def target_temperature(self) -> float | None:
        """The DHW setpoint."""
        return self.device.dhw.setpoint

    @property
    def current_operation(self) -> str | None:
        """Whether DHW generation is enabled."""
        enabled = self.device.dhw.enabled
        if enabled is None:
            return None
        return STATE_ELECTRIC if enabled else STATE_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write the DHW setpoint."""
        if (target := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        try:
            await self.device.dhw.set_setpoint(target)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Enable or disable DHW generation."""
        await self.device.dhw.set_enabled(operation_mode == STATE_ELECTRIC)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable DHW generation."""
        await self.async_set_operation_mode(STATE_ELECTRIC)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable DHW generation."""
        await self.async_set_operation_mode(STATE_OFF)
