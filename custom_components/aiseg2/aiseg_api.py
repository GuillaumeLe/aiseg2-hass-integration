"""API utilities for Panasonic Aiseg."""

from abc import ABC
import asyncio
from enum import StrEnum
import functools

from lxml import html
import requests
from requests.auth import HTTPDigestAuth


class AisegEntityType(StrEnum):
    """Enum class for entity types."""

    ENERGY = "energy"
    POWER = "power"
    SWITCH = "switch"


class AisegResourceKey(StrEnum):
    """Enum class for resources keys."""

    TODAY_ELECTRICITY_USAGE = "today_electricity_usage"
    TODAY_ELECTRICITY_GRID_CONSUMPTION = "today_electricity_grid_consumption"
    TODAY_ELECTRICITY_RETURN_TO_GRID = "today_electricity_return_to_grid"
    TODAY_ELECTRICITY_PRODUCTION = "today_electricity_production"
    CURRENT_CONSUMPTION = "current_consumption"
    CURRENT_PRODUCTION = "current_production"
    NOTIFICATION_ENABLED = "notification_enabled"


class ResourceScrapingConfig:
    """Helper class to define scraping config for a ressource."""

    def __init__(self, path: str, xpath: str) -> None:
        """Initialize."""
        self.path = path
        self.xpath = xpath


resourceScrapingConfigs: dict[AisegResourceKey, ResourceScrapingConfig] = {
    AisegResourceKey.CURRENT_CONSUMPTION: ResourceScrapingConfig(
        "/page/electricflow/111", '//div[@id="u_capacity"]/text()',
    ),
    AisegResouceKey.CURRENT_PRODUCTION: ResourceScrapingConfig(
      "/page/electricflow/111", '//div[@id="g_capacity"]/text()'
    ),
    AisegResourceKey.TODAY_ELECTRICITY_GRID_CONSUMPTION: ResourceScrapingConfig(
        "/page/graph/53111", '//span[@id="val_kwh"]/text()'
    ),
    AisegResourceKey.TODAY_ELECTRICITY_PRODUCTION: ResourceScrapingConfig(
        "/page/graph/51111", '//span[@id="val_kwh"]/text()'
    ),
    AisegResourceKey.TODAY_ELECTRICITY_USAGE: ResourceScrapingConfig(
        "/page/graph/52111", '//span[@id="val_kwh"]/text()'
    ),
    AisegResourceKey.TODAY_ELECTRICITY_RETURN_TO_GRID: ResourceScrapingConfig(
        "/page/graph/54111", '//span[@id="val_kwh"]/text()'
    ),
}


class AisegAPI:
    """API object to interact with Aiseg."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize."""
        self.host = host
        self.username = username
        self.password = password

    async def _execute_request(self, path):
        url = "http://" + self.host + path
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(
                requests.get,
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                timeout=1000,
            ),
        )

    async def fetch_resource(self, config: ResourceScrapingConfig):
        """Fetch resource value from config."""
        response = await self._execute_request(config.path)
        root = html.fromstring(response.content)
        return root.xpath(config.xpath).pop()

    async def _fetch_notification_enabled(self):
        response = await self._execute_request("/page/setting/installation/73f2")
        root = html.fromstring(response.content)
        if len(root.xpath('//div[contains(@class,"radio_on")][@id="radio_1"]')) > 0:
            return False
        if len(root.xpath('//div[contains(@class,"radio_on")][@id="radio_2"]')) > 0:
            return True
        return False

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        response = await self._execute_request("/")
        return response.status_code

    async def get_device(self):
        """Get device information."""
        # TODO fix parser
        # response = await self._execute_request("/page/setting/etc/743")
        # root = html.fromstring(response.content)
        # name = root.xpath('//div[@id="table_wrapper1"]/table/tbody/tr[2]/td')[0].text
        # device_id = root.xpath('//div[@id="table_wrapper1"]/table/tbody/tr[5]/td')[
        #     0
        # ].text
        name = "AiSEG2"
        device_id = 42
        return AisegDevice(name, device_id)

    async def fetch_data(self):
        """Fetch data."""
        data: list[AisegSensor] = [
            AisegEnergySensor(AisegResourceKey.TODAY_ELECTRICITY_USAGE, self),
            AisegEnergySensor(
                AisegResourceKey.TODAY_ELECTRICITY_GRID_CONSUMPTION,
                self,
            ),
            AisegEnergySensor(
                AisegResourceKey.TODAY_ELECTRICITY_RETURN_TO_GRID,
                self,
            ),
            AisegEnergySensor(
                AisegResourceKey.TODAY_ELECTRICITY_PRODUCTION,
                self,
            ),
            AisegPowerSensor(AisegResourceKey.CURRENT_CONSUMPTION, self),
            AisegSwitch(AisegResourceKey.NOTIFICATION_ENABLED, self),
        ]
        for item in data:
            await item.update()
        return data


class AisegSensor(ABC, AisegAPI):
    """Abstract class to instanciate sensor."""

    def __init__(self, key: AisegResourceKey, api: AisegAPI) -> None:
        """Initialize."""
        super().__init__(api.host, api.username, api.password)
        self.key = key
        self.value = None

    def getValue(self):
        """Get sensor value."""
        return self.value

    def getKey(self) -> str:
        """Get sensor key."""
        return self.key

    async def update(self):
        """Update sensor value."""
        self.value = await self.fetch_resource(resourceScrapingConfigs[self.key])
        return self.value


class AisegEnergySensor(AisegSensor):
    """Implementation of the AisegSensor class for energy sensors."""

    type = AisegEntityType.ENERGY
    time_range = "day"


class AisegPowerSensor(AisegSensor):
    """Implementation of the AisegSensor class for power sensors."""

    type = AisegEntityType.POWER


class AisegSwitch(AisegSensor):
    """Implementation of the AisegSensor class for configuration switches."""

    type = AisegEntityType.SWITCH

    async def update(self):
        """Update sensor value."""
        self.value = await self._fetch_notification_enabled()
        return self.value


class AisegDevice:
    """Class to store data about AiSEG2 Device."""

    def __init__(self, name, device_id) -> None:
        """Initialize."""
        self.name = name
        self.device_id = device_id
        self.manufacturer = "Panasonic"
