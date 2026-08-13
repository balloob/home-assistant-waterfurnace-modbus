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

    def __init__(
        self,
        coordinator: AuroraCoordinator,
        key: str,
        *,
        components: tuple[str, ...] = (),
    ) -> None:
        """Initialize identity from the config entry and the entity key.

        ``components`` names the library sub-systems this entity reads, as the
        poll's ``UpdateReport`` keys them; a poll that could not refresh one of
        them leaves the entity unavailable instead of showing a stale value.
        """
        super().__init__(coordinator)
        entry = coordinator.config_entry
        info = coordinator.device.info
        self._components = frozenset(components)
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
    def available(self) -> bool:
        """Whether the last poll refreshed the sub-systems this entity reads."""
        failed = self.coordinator.data.failed
        return super().available and not self._components & failed.keys()

    @property
    def device(self) -> Series7:
        """The shared device object entities read their values from."""
        return self.coordinator.device
