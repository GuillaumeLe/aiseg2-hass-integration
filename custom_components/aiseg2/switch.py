"""Platform for switch integration."""

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AisegConfigEntry
from .aiseg_api import AisegEntityType
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
    device_info = coordinator.getDeviceInfo()
    switch_entities = [
        NotificationEnableSwitch(
            coordinator, item.getKey(), item.getValue(), device_info
        )
        for item in coordinator.data.getByType(AisegEntityType.SWITCH)
    ]

    async_add_entities(switch_entities)


class NotificationEnableSwitch(CoordinatorEntity, SwitchEntity):
    """Entity to manipulate AiSEG config switch."""

    __attr_name = "notification_enabled"
    __attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self, coordinator: AisegPoolingCoordinator, idx, initial_value, device_info
    ) -> None:
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
        item = self.coordinator.data.get(self.idx)
        self.is_on = item.getValue()
        self.async_write_ha_state()
