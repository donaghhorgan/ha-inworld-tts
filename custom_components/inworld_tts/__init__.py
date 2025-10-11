"""The Inworld TTS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.TTS]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Inworld TTS from a config entry."""
    _LOGGER.debug(
        "Setting up Inworld TTS integration from config entry: %s", entry.entry_id
    )
    _LOGGER.debug(
        "Config entry data: %s",
        {k: "***" if "key" in k.lower() else v for k, v in entry.data.items()},
    )
    _LOGGER.debug("Config entry options: %s", entry.options)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Inworld TTS integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(
        "Unloading Inworld TTS integration for config entry: %s", entry.entry_id
    )
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        _LOGGER.debug("Inworld TTS integration unloaded successfully")
    else:
        _LOGGER.debug("Failed to unload Inworld TTS integration")
    return result
