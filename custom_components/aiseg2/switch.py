"""Platform for switch integration."""

from datetime import timedelta

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AisegConfigEntry
from .aiseg_api import AisegEntityType, AisegSwitch
from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AisegConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config entry example."""
    my_api = entry.runtime_data

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    data = await my_api.fetch_data()
    device = await my_api.get_device()
    if device is not None:
        device_info = {
            "name": device.name,
            "identifiers": {(DOMAIN, device.device_id)},
            "manufacturer": device.manufacturer,
        }
    else:
        device_info = {}

    switch_entities = [
        NotificationEnableSwitch(item, item.getKey(), item.getValue(), device_info)
        for item in filter(lambda datum: datum.type == AisegEntityType.SWITCH, data)
    ]

    async_add_entities(switch_entities)


class NotificationEnableSwitch(SwitchEntity):
    """Entity to manipulate AiSEG config switch."""

    __attr_name = "notification_enabled"
    __attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, switch: AisegSwitch, idx, initial_value, device_info) -> None:
        """Initialize."""
        self.idx = idx
        self.switch = switch
        self._attr_unique_id = idx
        self._attr_name = idx
        self.is_on = initial_value
        self._attr_device_info = device_info
        self.is_on = False

    async def async_update(self):
        """Update switch state."""
        self.is_on = self.switch.getValue()
