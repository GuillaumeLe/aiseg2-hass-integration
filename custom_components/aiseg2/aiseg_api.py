"""API utilities for Panasonic Aiseg."""

import asyncio
import functools

from lxml import html
import requests
from requests.auth import HTTPDigestAuth


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

    async def _fetch_today_electricity_usage(self):
        response = await self._execute_request("/page/graph/52111")
        root = html.fromstring(response.content)
        return root.xpath('//span[@id="val_kwh"]')[0].text

    async def _fetch_today_electricity_grid_consumption(self):
        response = await self._execute_request("/page/graph/53111")
        root = html.fromstring(response.content)
        return root.xpath('//span[@id="val_kwh"]')[0].text

    async def _fetch_today_electricity_return_to_grid(self):
        response = await self._execute_request("/page/graph/54111")
        root = html.fromstring(response.content)
        return root.xpath('//span[@id="val_kwh"]')[0].text

    async def _fetch_today_electricity_production(self):
        response = await self._execute_request("/page/graph/51111")
        root = html.fromstring(response.content)
        return root.xpath('//span[@id="val_kwh"]')[0].text

    async def _fetch_current_consumption(self):
        response = await self._execute_request("/page/electricflow/111")
        root = html.fromstring(response.content)
        return root.xpath("/html/body/div[2]/div/div[4]/div[2]/div[2]/div[2]/text()")[0]

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

    async def fetch_data(self, entities):
        """Fetch data."""
        return {
            "energy": {
                "today_electricity_usage": await self._fetch_today_electricity_usage(),
                "today_electricity_grid_consumption": await self._fetch_today_electricity_grid_consumption(),
                "today_electricity_return_to_grid": await self._fetch_today_electricity_return_to_grid(),
                "today_electricity_production": await self._fetch_today_electricity_production(),
            },
            "power": {
                "current_consumption": await self._fetch_current_consumption(),
            },
        }


class AisegDevice:
    """Class to store data about AiSEG2 Device."""

    def __init__(self, name, device_id) -> None:
        """Initialize."""
        self.name = name
        self.device_id = device_id
        self.manufacturer = "Panasonic"
