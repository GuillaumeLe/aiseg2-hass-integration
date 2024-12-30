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
from .const import DOMAIN
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
    if coordinator.getDevice() is not None:
        device_info = {
            "name": coordinator.getDevice().name,
            "identifiers": {(DOMAIN, coordinator.getDevice().device_id)},
            "manufacturer": coordinator.getDevice().manufacturer,
        }
    else:
        device_info = {}
    energy_entities = []
    power_entities = []
    for item in coordinator.data:
        match item.type:
            case AisegEntityType.ENERGY:
                energy_entities.append(
                    EnergySensor(
                        coordinator,
                        item.getKey(),
                        item.getValue(),
                        device_info,
                        tz,
                    )
                )
            case AisegEntityType.POWER:
                power_entities.append(
                    PowerSensor(
                        coordinator,
                        item.getKey(),
                        item.getValue(),
                        device_info,
                    )
                )

    async_add_entities(energy_entities)
    async_add_entities(power_entities)


class PowerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Power"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value = 0

    def __init__(self, coordinator, idx, initial_value, device_info) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for item in self.coordinator.data:
            if item.getKey() == self.idx:
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

    def __init__(self, coordinator, idx, initial_value, device_info, tz) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.tz = tz
        self.idx = idx
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value
        self._attr_last_reset = self._get_today_start_time()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for item in self.coordinator.data:
            if item.getKey() == self.idx:
                self._attr_native_value = item.getValue()
                self._attr_last_reset = self._get_today_start_time()
                self.async_write_ha_state()
