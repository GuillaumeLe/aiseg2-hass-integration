"""The Aiseg2 Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from . import aiseg_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


type AisegConfigEntry = ConfigEntry[aiseg_api.AisegAPI]  # noqa: F821


async def async_setup_entry(hass: HomeAssistant, entry: AisegConfigEntry) -> bool:
    """Set up Aiseg2 Home Assistant from a config entry."""
    api = aiseg_api.AisegAPI(
        entry.data.get(CONF_HOST),
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
    )
    _LOGGER.debug("Aiseg API object initiliazed")
    if await api.authenticate():
        _LOGGER.debug("Aiseg authencation successful")
    else:
        _LOGGER.error("Aiseg authentication failed")
        return False

    entry.runtime_data = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AisegConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
