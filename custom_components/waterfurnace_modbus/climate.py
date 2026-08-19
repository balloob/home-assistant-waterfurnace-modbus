"""Climate: the communicating thermostat, and one entity per IZ2 zone."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity
from .vendor.waterfurnace_modbus import (
    FanMode,
    HeatingMode,
    SystemOutput,
    Thermostat,
    Zone,
    ZoneCall,
)

# EHEAT (electric-only emergency heat) is not an HVAC mode Home Assistant
# knows; it is exposed as a preset on top of heating instead.
PRESET_EMERGENCY_HEAT = "emergency_heat"
PRESET_NONE = "none"

_HVAC_TO_MODE: dict[HVACMode, HeatingMode] = {
    HVACMode.OFF: HeatingMode.OFF,
    HVACMode.HEAT_COOL: HeatingMode.AUTO,
    HVACMode.COOL: HeatingMode.COOL,
    HVACMode.HEAT: HeatingMode.HEAT,
}
_MODE_TO_HVAC: dict[HeatingMode, HVACMode] = {
    **{mode: hvac for hvac, mode in _HVAC_TO_MODE.items()},
    HeatingMode.EHEAT: HVACMode.HEAT,
}

_FAN_TO_MODE: dict[str, FanMode] = {
    "auto": FanMode.AUTO,
    "continuous": FanMode.CONTINUOUS,
    "intermittent": FanMode.INTERMITTENT,
}
_MODE_TO_FAN = {mode: name for name, mode in _FAN_TO_MODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the thermostat, and a zone entity per reported IZ2 zone."""
    coordinator = entry.runtime_data.readings
    entities: list[ClimateEntity] = [AuroraThermostat(coordinator)]
    entities.extend(
        AuroraZone(coordinator, zone, index)
        for index, zone in enumerate(coordinator.zones, start=1)
    )
    async_add_entities(entities)


class AuroraClimate(AuroraEntity, ClimateEntity):
    """Shared mode/setpoint/fan behavior of the thermostat and a zone."""

    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    _attr_fan_modes = list(_FAN_TO_MODE)
    _attr_preset_modes = [PRESET_NONE, PRESET_EMERGENCY_HEAT]
    # The Aurora setpoint windows: heating 40-90 °F, cooling 54-99 °F.
    _attr_min_temp = 40.0
    _attr_max_temp = 99.0

    @property
    def _component(self) -> Thermostat | Zone:
        raise NotImplementedError

    @property
    def _heating_target(self) -> float | None:
        raise NotImplementedError

    @property
    def _cooling_target(self) -> float | None:
        raise NotImplementedError

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Range setpoints in heat/cool, a single setpoint otherwise."""
        features = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )
        if self.hvac_mode is HVACMode.HEAT_COOL:
            return features | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        return features | ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def current_temperature(self) -> float | None:
        """Ambient at this thermostat or zone."""
        return self._component.ambient_temperature

    @property
    def hvac_mode(self) -> HVACMode | None:
        """The operating mode, with EHEAT folded into heating."""
        mode = self._component.mode
        return None if mode is None else _MODE_TO_HVAC[mode]

    @property
    def preset_mode(self) -> str | None:
        """Emergency heat, or none."""
        mode = self._component.mode
        if mode is None:
            return None
        return PRESET_EMERGENCY_HEAT if mode is HeatingMode.EHEAT else PRESET_NONE

    @property
    def fan_mode(self) -> str | None:
        """The fan mode by its Aurora name."""
        mode = self._component.fan_mode
        return None if mode is None else _MODE_TO_FAN[mode]

    @property
    def target_temperature(self) -> float | None:
        """The single setpoint the current mode heats or cools toward."""
        if self.hvac_mode is HVACMode.COOL:
            return self._cooling_target
        if self.hvac_mode is HVACMode.HEAT:
            return self._heating_target
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """The heating side of the heat/cool range."""
        return self._heating_target if self.hvac_mode is HVACMode.HEAT_COOL else None

    @property
    def target_temperature_high(self) -> float | None:
        """The cooling side of the heat/cool range."""
        return self._cooling_target if self.hvac_mode is HVACMode.HEAT_COOL else None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the operating mode."""
        await self._component.set_mode(_HVAC_TO_MODE[hvac_mode])
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Enter or leave emergency (electric-only) heat."""
        mode = (
            HeatingMode.EHEAT
            if preset_mode == PRESET_EMERGENCY_HEAT
            else HeatingMode.HEAT
        )
        await self._component.set_mode(mode)
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        await self._component.set_fan_mode(_FAN_TO_MODE[fan_mode])
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write the setpoint(s) the service call carries."""
        try:
            if (low := kwargs.get(ATTR_TARGET_TEMP_LOW)) is not None:
                await self._component.set_heating_setpoint(low)
            if (high := kwargs.get(ATTR_TARGET_TEMP_HIGH)) is not None:
                await self._component.set_cooling_setpoint(high)
            if (target := kwargs.get(ATTR_TEMPERATURE)) is not None:
                if self.hvac_mode is HVACMode.COOL:
                    await self._component.set_cooling_setpoint(target)
                else:
                    await self._component.set_heating_setpoint(target)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class AuroraThermostat(AuroraClimate):
    """The unit-wide communicating thermostat."""

    _attr_name = None  # takes the device name

    def __init__(self, coordinator: AuroraCoordinator) -> None:
        """Initialize the thermostat entity."""
        # hvac_action reads the controller's outputs, not the thermostat block.
        super().__init__(coordinator, "thermostat", components=("thermostat", "status"))

    @property
    def current_temperature(self) -> float | None:
        """Ambient at the thermostat, which reports it with the measurements."""
        return self.coordinator.device.sensors.ambient_air

    @property
    def _component(self) -> Thermostat:
        return self.device.thermostat

    @property
    def _heating_target(self) -> float | None:
        return self._component.heating_setpoint

    @property
    def _cooling_target(self) -> float | None:
        return self._component.cooling_setpoint

    @property
    def hvac_action(self) -> HVACAction | None:
        """What the unit is doing, from the controller's active outputs."""
        outputs = self.device.status.outputs
        if outputs is None:
            return None
        if self.hvac_mode is HVACMode.OFF:
            return HVACAction.OFF
        if SystemOutput.COMPRESSOR_1 in outputs:
            # The reversing valve is energized for cooling.
            if SystemOutput.REVERSING_VALVE in outputs:
                return HVACAction.COOLING
            return HVACAction.HEATING
        if SystemOutput.AUX_HEAT_1 in outputs:
            return HVACAction.HEATING
        if SystemOutput.BLOWER in outputs:
            return HVACAction.FAN
        return HVACAction.IDLE


class AuroraZone(AuroraClimate):
    """One IntelliZone 2 zone."""

    _attr_translation_key = "zone"

    def __init__(self, coordinator: AuroraCoordinator, zone: Zone, index: int) -> None:
        """Initialize a zone entity."""
        # The report keys zones the same way, off their live_zones position.
        super().__init__(coordinator, f"zone_{index}", components=(f"zone_{index}",))
        self._zone = zone
        self._attr_translation_placeholders = {"zone": str(index)}

    @property
    def _component(self) -> Zone:
        return self._zone

    @property
    def _heating_target(self) -> float | None:
        return self._zone.heating_target

    @property
    def _cooling_target(self) -> float | None:
        return self._zone.cooling_target

    @property
    def hvac_action(self) -> HVACAction | None:
        """What this zone is calling for."""
        call = self._zone.call
        if call is None:
            return None
        if self.hvac_mode is HVACMode.OFF:
            return HVACAction.OFF
        if call in (ZoneCall.HEAT_1, ZoneCall.HEAT_2, ZoneCall.HEAT_3):
            return HVACAction.HEATING
        if call in (ZoneCall.COOL_1, ZoneCall.COOL_2):
            return HVACAction.COOLING
        return HVACAction.IDLE
