"""Aiseg."""

from asyncio import timeout
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aiseg_api import (
    AisegAPI,
    AisegDevice,
    AisegEntityType,
    AisegSensor,
    ApiAuthError,
    ApiError,
    ScrapingError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DataContainer:
    """Utiliy container to manage integration data."""

    def __init__(self, data: list[AisegSensor]) -> None:
        """Initialize."""
        self.map: dict[str, AisegSensor] = {}
        for item in data:
            self.map[item.getKey()] = item

    def get(self, key: str) -> AisegSensor:
        """Get Entity with key."""
        try:
            return self.map.get(key)
        except KeyError:
            return None

    def set(self, item: AisegSensor) -> None:
        """Set Entity to container."""
        self.map[item.getKey()] = item

    def getByType(self, entity_type: AisegEntityType) -> list[AisegSensor]:
        """Get all entity with the given type."""
        return filter(lambda item: item.type == entity_type, self.map.values())

    def __eq__(self, other: object):
        """Check equality."""
        if not isinstance(other, DataContainer):
            return NotImplemented
        if len(self.map.keys()) != len(other.map.keys()):
            return False
        for key in self.map:
            if other.get(key).getValue() != self.get(key).getValue():
                return False
        return True

    def __len__(self):
        """Get number of entity in the container."""
        return len(self.map.keys())


class AisegPoolingCoordinator(DataUpdateCoordinator[DataContainer]):
    """My custom coordinator."""

    def __init__(
        self, hass: HomeAssistant, my_api: AisegAPI, update_interval: int = 30
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Aiseg energy",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=update_interval),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False,
        )
        self.my_api = my_api
        self._device: AisegDevice | None = None

    def getDeviceInfo(self):
        """Get device information to link entities."""
        if self._device is not None:
            return {
                "name": self._device.name,
                "identifiers": {(DOMAIN, self._device.device_id)},
                "manufacturer": self._device.manufacturer,
            }
        return {}

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        self._device = await self.my_api.get_device()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                listening_idx = set(self.async_contexts())
                if self.data is None or len(self.data) == 0:
                    data = await self.my_api.fetch_data()
                    return DataContainer(data)
                for key in listening_idx:
                    await self.data.get(key).update()
                return self.data

        except ApiAuthError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except ScrapingError as err:
            raise UpdateFailed("Err while parsing API response") from err
        except Exception as err:
            raise UpdateFailed("Err updating sensor") from err
