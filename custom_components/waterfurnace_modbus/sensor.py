"""Sensors: temperatures, pressures, flow, speeds, powers and faults."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity
from .vendor.waterfurnace_modbus import EnergyMonitorType, Series7


@dataclass(frozen=True, kw_only=True)
class AuroraSensorDescription(SensorEntityDescription):
    """Describes an Aurora sensor as a read off the device object."""

    component: str  # the sub-system value_fn reads, as the UpdateReport keys it
    value_fn: Callable[[Series7], float | int | str | None]


def _temperature(
    key: str,
    component: str,
    value_fn: Callable[[Series7], float | None],
    *,
    diagnostic: bool = False,
) -> AuroraSensorDescription:
    """A °F temperature sensor description."""
    return AuroraSensorDescription(
        key=key,
        translation_key=key,
        component=component,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        value_fn=value_fn,
    )


def _power(
    key: str, value_fn: Callable[[Series7], int | None]
) -> AuroraSensorDescription:
    """A watt power sensor description (AXB energy-monitor package)."""
    return AuroraSensorDescription(
        key=key,
        translation_key=key,
        component="energy",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=value_fn,
    )


SENSORS: tuple[AuroraSensorDescription, ...] = (
    # -- water loop --
    _temperature("entering_water", "sensors", lambda d: d.sensors.entering_water),
    _temperature("leaving_water", "sensors", lambda d: d.sensors.leaving_water),
    AuroraSensorDescription(
        key="waterflow",
        translation_key="waterflow",
        component="pump",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.GALLONS_PER_MINUTE,
        value_fn=lambda d: d.pump.waterflow,
    ),
    AuroraSensorDescription(
        key="loop_pressure",
        translation_key="loop_pressure",
        component="pump",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PSI,
        value_fn=lambda d: d.pump.loop_pressure,
    ),
    AuroraSensorDescription(
        key="pump_output",
        translation_key="pump_output",
        component="pump",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.pump.output,
    ),
    # -- air --
    _temperature("entering_air", "sensors", lambda d: d.sensors.entering_air),
    _temperature("leaving_air", "sensors", lambda d: d.sensors.leaving_air),
    _temperature("outdoor", "sensors", lambda d: d.sensors.outdoor),
    AuroraSensorDescription(
        key="relative_humidity",
        translation_key="relative_humidity",
        component="sensors",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.sensors.relative_humidity,
    ),
    # -- compressor (VS drive) --
    AuroraSensorDescription(
        key="compressor_speed",
        translation_key="compressor_speed",
        component="compressor",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.compressor.speed_actual,
    ),
    AuroraSensorDescription(
        key="discharge_pressure",
        translation_key="discharge_pressure",
        component="compressor",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PSI,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.compressor.discharge_pressure,
    ),
    AuroraSensorDescription(
        key="suction_pressure",
        translation_key="suction_pressure",
        component="compressor",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PSI,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.compressor.suction_pressure,
    ),
    _temperature(
        "discharge_temperature",
        "compressor",
        lambda d: d.compressor.discharge_temperature,
        diagnostic=True,
    ),
    _temperature(
        "superheat", "compressor", lambda d: d.compressor.superheat, diagnostic=True
    ),
    # -- blower --
    AuroraSensorDescription(
        key="blower_speed",
        translation_key="blower_speed",
        component="blower",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.blower.speed,
    ),
    # -- status --
    AuroraSensorDescription(
        key="line_voltage",
        translation_key="line_voltage",
        component="status",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.line_voltage,
    ),
    AuroraSensorDescription(
        key="aux_heat_stage",
        translation_key="aux_heat_stage",
        component="status",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.aux_heat_stage,
    ),
    AuroraSensorDescription(
        key="fault",
        translation_key="fault",
        component="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.fault or "none",
    ),
)

# Populated only with the AXB energy-monitor package; without it these
# registers read 0, which would show as a wall of zero-watt sensors.
ENERGY_SENSORS: tuple[AuroraSensorDescription, ...] = (
    _power("total_power", lambda d: d.energy.total_power),
    _power("compressor_power", lambda d: d.energy.compressor_power),
    _power("blower_power", lambda d: d.energy.blower_power),
    _power("pump_power", lambda d: d.energy.pump_power),
    _power("aux_power", lambda d: d.energy.aux_power),
    AuroraSensorDescription(
        key="heat_of_extraction",
        translation_key="heat_of_extraction",
        component="energy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.BTU_PER_HOUR,
        value_fn=lambda d: d.energy.heat_of_extraction,
    ),
    AuroraSensorDescription(
        key="heat_of_rejection",
        translation_key="heat_of_rejection",
        component="energy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.BTU_PER_HOUR,
        value_fn=lambda d: d.energy.heat_of_rejection,
    ),
    AuroraSensorDescription(
        key="compressor_amps",
        translation_key="compressor_amps",
        component="compressor",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.compressor.stage_1_amps,
    ),
    AuroraSensorDescription(
        key="blower_amps",
        translation_key="blower_amps",
        component="blower",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.blower.amps,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors the installed hardware supports."""
    coordinator = entry.runtime_data
    descriptions = list(SENSORS)
    if coordinator.device.config.energy_monitor is EnergyMonitorType.ENERGY_MONITOR:
        descriptions.extend(ENERGY_SENSORS)
    async_add_entities(
        AuroraSensor(coordinator, description) for description in descriptions
    )


class AuroraSensor(AuroraEntity, SensorEntity):
    """A value read straight off the device object."""

    entity_description: AuroraSensorDescription

    def __init__(
        self, coordinator: AuroraCoordinator, description: AuroraSensorDescription
    ) -> None:
        """Initialize from the description."""
        super().__init__(
            coordinator, description.key, components=(description.component,)
        )
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        """The current decoded value."""
        return self.entity_description.value_fn(self.device)
