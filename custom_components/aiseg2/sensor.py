"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import async_get_time_zone

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
    coordinator = AisegPoolingCoordinator(hass, my_api)

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    #
    tz = await async_get_time_zone(hass.config.time_zone)
    await coordinator.async_config_entry_first_refresh()
    device_info = coordinator.getDeviceInfo()
    energy_entities = [
        EnergySensor(coordinator, item.getKey(), item.getValue(), device_info, tz)
        for item in coordinator.data.getByType(AisegEntityType.ENERGY)
    ]
    power_entities = [
        PowerSensor(coordinator, item.getKey(), item.getValue(), device_info)
        for item in coordinator.data.getByType(AisegEntityType.POWER)
    ]
    async_add_entities(energy_entities)
    async_add_entities(power_entities)


class PowerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Power"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value = 0

    def __init__(
        self, coordinator: AisegPoolingCoordinator, idx, initial_value, device_info
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value

    @property
    def translation_key(self):
        return self._attr_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item = self.coordinator.data.get(self.idx)
        self._attr_native_value = item.getValue()
        self.async_write_ha_state()


class EnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_value = 0

    def _get_today_start_time(self):
        return (
            datetime.today()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(self.tz)
        )

    def __init__(
        self, coordinator: AisegPoolingCoordinator, idx, initial_value, device_info, tz
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.tz = tz
        self.idx = idx
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value
        self._attr_last_reset = self._get_today_start_time()

    @property
    def translation_key(self):
        return self._attr_name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item = self.coordinator.data.get(self.idx)
        self._attr_native_value = item.getValue()
        self._attr_last_reset = self._get_today_start_time()
        self.async_write_ha_state()
