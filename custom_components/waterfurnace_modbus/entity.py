"""Base entity: shared device info and identity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AuroraCoordinator
from .vendor.waterfurnace_modbus import Series7


class AuroraEntity(CoordinatorEntity[AuroraCoordinator]):
    """One heat pump is one Home Assistant device; every entity hangs off it."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AuroraCoordinator, key: str) -> None:
        """Initialize identity from the config entry and the entity key."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        info = coordinator.device.info
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=info.manufacturer,
            model=info.model,
            name=entry.title,
            serial_number=info.serial_number,
            sw_version=info.firmware_version,
        )

    @property
    def device(self) -> Series7:
        """The shared device object entities read their values from."""
        return self.coordinator.device
