"""LOE Lviv Outages entity."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LoeOutagesCoordinator


class LoeOutagesEntity(CoordinatorEntity[LoeOutagesCoordinator]):
    """Common logic for LOE Lviv Outages entity."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            translation_key="loe_lviv_outages",
            translation_placeholders={
                "group": str(self.coordinator.group),
            },
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer="Львівобленерго",
            entry_type=DeviceEntryType.SERVICE,
        )
