"""Platform for switch integration."""

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AisegConfigEntry
from .aiseg_api import AisegEntityType
from .const import DOMAIN
from .coordinator import AisegPoolingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AisegConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config entry example."""
    my_api = entry.runtime_data
    coordinator = AisegPoolingCoordinator(hass, my_api, update_interval=10)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    await coordinator.async_config_entry_first_refresh()
    if coordinator.getDevice() is not None:
        device_info = {
            "name": coordinator.getDevice().name,
            "identifiers": {(DOMAIN, coordinator.getDevice().device_id)},
            "manufacturer": coordinator.getDevice().manufacturer,
        }
    else:
        device_info = {}
    switch_entities = []
    for item in coordinator.data:
        match item.type:
            case AisegEntityType.SWITCH:
                switch_entities.append(
                    NotificationEnableSwitch(
                        coordinator, item.getKey(), item.getValue(), device_info
                    )
                )

    async_add_entities(switch_entities)


class NotificationEnableSwitch(CoordinatorEntity, SwitchEntity):
    __attr_name = "notification_enabled"
    __attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator, idx, initial_value, device_info) -> None:
        """Initialize."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self._attr_unique_id = idx
        self._attr_name = idx
        self.is_on = initial_value
        self._attr_device_info = device_info
        self.is_on = False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for item in self.coordinator.data:
            if item.getKey() == self.idx:
                self.is_on = item.getValue()
                self.async_write_ha_state()
