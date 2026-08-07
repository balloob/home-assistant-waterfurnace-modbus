"""Binary sensors: what's running, and the safety/problem states."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity
from .vendor.waterfurnace_modbus import Series7, SystemOutput


def _output(device: Series7, flag: SystemOutput) -> bool | None:
    """Whether an output flag is active, or None before the first read."""
    outputs = device.status.outputs
    return None if outputs is None else flag in outputs


@dataclass(frozen=True, kw_only=True)
class AuroraBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an Aurora on/off state as a read off the device object."""

    value_fn: Callable[[Series7], bool | None]


BINARY_SENSORS: tuple[AuroraBinarySensorDescription, ...] = (
    AuroraBinarySensorDescription(
        key="compressor_running",
        translation_key="compressor_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _output(d, SystemOutput.COMPRESSOR_1),
    ),
    AuroraBinarySensorDescription(
        key="blower_running",
        translation_key="blower_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _output(d, SystemOutput.BLOWER),
    ),
    AuroraBinarySensorDescription(
        key="aux_heat",
        translation_key="aux_heat",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda d: _output(d, SystemOutput.AUX_HEAT_1),
    ),
    AuroraBinarySensorDescription(
        key="active_dehumidification",
        translation_key="active_dehumidification",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: d.humidistat.active_dehumidification,
    ),
    AuroraBinarySensorDescription(
        key="locked_out",
        translation_key="locked_out",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.locked_out,
    ),
    AuroraBinarySensorDescription(
        key="emergency_shutdown",
        translation_key="emergency_shutdown",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.emergency_shutdown,
    ),
    # The switches read set when closed — the healthy state — so "open" is
    # the problem this sensor reports.
    AuroraBinarySensorDescription(
        key="low_pressure_switch_open",
        translation_key="low_pressure_switch_open",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _invert(d.status.low_pressure_switch_closed),
    ),
    AuroraBinarySensorDescription(
        key="high_pressure_switch_open",
        translation_key="high_pressure_switch_open",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _invert(d.status.high_pressure_switch_closed),
    ),
    AuroraBinarySensorDescription(
        key="load_shed",
        translation_key="load_shed",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status.load_shed,
    ),
)


def _invert(value: bool | None) -> bool | None:
    """Invert a tri-state bool, keeping unknown unknown."""
    return None if value is None else not value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_add_entities(
        AuroraBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class AuroraBinarySensor(AuroraEntity, BinarySensorEntity):
    """An on/off state read straight off the device object."""

    entity_description: AuroraBinarySensorDescription

    def __init__(
        self,
        coordinator: AuroraCoordinator,
        description: AuroraBinarySensorDescription,
    ) -> None:
        """Initialize from the description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """The current decoded state."""
        return self.entity_description.value_fn(self.device)
