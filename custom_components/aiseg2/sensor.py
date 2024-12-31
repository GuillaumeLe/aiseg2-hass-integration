"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import async_get_time_zone

from . import AisegConfigEntry
from .aiseg_api import AisegEnergySensor, AisegEntityType, AisegPowerSensor
from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)


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
    tz = await async_get_time_zone(hass.config.time_zone)
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

    energy_entities = [
        EnergySensor(item, item.getKey(), item.getValue(), device_info, tz)
        for item in filter(lambda datum: datum.type == AisegEntityType.ENERGY, data)
    ]
    power_entities = [
        PowerSensor(item, item.getKey(), item.getValue(), device_info)
        for item in filter(lambda datum: datum.type == AisegEntityType.POWER, data)
    ]
    async_add_entities(energy_entities)
    async_add_entities(power_entities)


class PowerSensor(SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Power"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_value = 0

    def __init__(
        self, sensor: AisegPowerSensor, idx, initial_value, device_info
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        self.idx = idx
        self.sensor = sensor
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value

    @property
    def translation_key(self):
        return self._attr_name

    async def async_update(self) -> None:
        """Update sensor value."""
        self._attr_native_value = await self.sensor.update()


class EnergySensor(SensorEntity):
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
        self, sensor: AisegEnergySensor, idx, initial_value, device_info, tz
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        self.tz = tz
        self.idx = idx
        self.sensor = sensor
        self._attr_unique_id = idx
        self._attr_device_info = device_info
        self._attr_name = idx
        self._attr_native_value = initial_value
        self._attr_last_reset = self._get_today_start_time()

    @property
    def translation_key(self):
        return self._attr_name

    async def async_update(self) -> None:
        """Update sensor value."""
        self._attr_native_value = await self.sensor.update()
        self._attr_last_reset = self._get_today_start_time()
