"""Numbers: the installer-level ECM blower and loop-pump speed settings."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AuroraConfigEntry, AuroraCoordinator
from .entity import AuroraEntity
from .vendor.waterfurnace_modbus import Series7


@dataclass(frozen=True, kw_only=True)
class AuroraNumberDescription(NumberEntityDescription):
    """Describes an installer setting: a read plus its setter."""

    component: str  # the sub-system value_fn reads, as the UpdateReport keys it
    value_fn: Callable[[Series7], int | None]
    set_fn: Callable[[Series7, int], Awaitable[None]]


def _ecm_speed(
    key: str,
    component: str,
    value_fn: Callable[[Series7], int | None],
    set_fn: Callable[[Series7, int], Awaitable[None]],
) -> AuroraNumberDescription:
    """An ECM speed-stage preset (1-12)."""
    return AuroraNumberDescription(
        key=key,
        translation_key=key,
        component=component,
        native_min_value=1,
        native_max_value=12,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=value_fn,
        set_fn=set_fn,
    )


# Installer-level settings, so disabled by default: enable them consciously.
NUMBERS: tuple[AuroraNumberDescription, ...] = (
    _ecm_speed(
        "blower_only_speed",
        "blower",
        lambda d: d.blower.blower_only_speed,
        lambda d, v: d.blower.set_blower_only_speed(v),
    ),
    _ecm_speed(
        "low_compressor_speed",
        "blower",
        lambda d: d.blower.low_compressor_speed,
        lambda d, v: d.blower.set_low_compressor_speed(v),
    ),
    _ecm_speed(
        "high_compressor_speed",
        "blower",
        lambda d: d.blower.high_compressor_speed,
        lambda d, v: d.blower.set_high_compressor_speed(v),
    ),
    _ecm_speed(
        "aux_heat_speed",
        "blower",
        lambda d: d.blower.aux_heat_speed,
        lambda d, v: d.blower.set_aux_heat_speed(v),
    ),
    AuroraNumberDescription(
        key="pump_minimum_speed",
        translation_key="pump_minimum_speed",
        component="pump",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.pump.minimum_speed,
        set_fn=lambda d, v: d.pump.set_minimum_speed(v),
    ),
    AuroraNumberDescription(
        key="pump_maximum_speed",
        translation_key="pump_maximum_speed",
        component="pump",
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.pump.maximum_speed,
        set_fn=lambda d, v: d.pump.set_maximum_speed(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AuroraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the installer-setting numbers."""
    async_add_entities(
        AuroraNumber(entry.runtime_data, description) for description in NUMBERS
    )


class AuroraNumber(AuroraEntity, NumberEntity):
    """An installer setting with a bounded write."""

    entity_description: AuroraNumberDescription

    def __init__(
        self, coordinator: AuroraCoordinator, description: AuroraNumberDescription
    ) -> None:
        """Initialize from the description."""
        super().__init__(
            coordinator, description.key, components=(description.component,)
        )
        self.entity_description = description

    @property
    def native_value(self) -> int | None:
        """The current setting."""
        return self.entity_description.value_fn(self.device)

    async def async_set_native_value(self, value: float) -> None:
        """Write the setting."""
        try:
            await self.entity_description.set_fn(self.device, int(value))
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
