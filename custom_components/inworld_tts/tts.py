"""Support for Inworld TTS service."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import requests
from homeassistant.components.tts import (
    TextToSpeechEntity,
    TtsAudioType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEFAULT_API_TIMEOUT,
    DOMAIN,
    TITLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inworld TTS from config entry."""
    async_add_entities([InworldTTSEntity(config_entry)])


class InworldTTSEntity(TextToSpeechEntity):
    """Inworld TTS speech service."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize Inworld TTS."""
        self._config_entry = config_entry
        self._attr_name = TITLE
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}"

    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with error handling."""
        if key not in self._config_entry.data:
            if default is not None:
                return default
            raise ValueError(f"Required configuration '{key}' is not set")
        return self._config_entry.data[key]

    @property
    def _api_url(self) -> str:
        """Get API URL from config."""
        return self._get_config_value("api_url")

    @property
    def _api_key(self) -> str:
        """Get API key from config."""
        return self._get_config_value("api_key")

    @property
    def _voice_id(self) -> str:
        """Get voice ID from config."""
        return self._get_config_value("voice_id")

    @property
    def _model_id(self) -> str:
        """Get model ID from config."""
        return self._get_config_value("model_id")

    @property
    def _language(self) -> str:
        """Get language from config."""
        return self._get_config_value("language")

    @property
    def _audio_encoding(self) -> str:
        """Get audio encoding from config."""
        return self._get_config_value("audio_encoding")

    @property
    def _sample_rate_hertz(self) -> int:
        """Get sample rate from config."""
        return self._get_config_value("sample_rate_hertz")

    @property
    def _temperature(self) -> float:
        """Get temperature from config."""
        return self._get_config_value("temperature")

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        try:
            return [self._language]
        except ValueError:
            # If language is not configured, return empty list
            return []

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return self._language

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options like voice."""
        return ["voice"]

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options."""
        try:
            return {"voice": self._voice_id}
        except ValueError:
            # If voice_id is not configured, return empty dict
            return {}

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Load TTS from Inworld."""
        try:
            if language != self._language:
                raise Exception(f"Language '{language}' not supported")

            # Get voice from options if provided, otherwise use default
            voice_id = self._voice_id
            if options and "voice" in options:
                voice_id = options["voice"]

            url = f"{self._api_url}/tts/v1/voice"
            headers = {
                "Authorization": f"Basic {self._api_key}",
                "Content-Type": "application/json",
            }

            # Prepare audio config based on format
            payload = {
                "text": message,
                "voiceId": voice_id,
                "modelId": self._model_id,
                "temperature": self._temperature,
                "audioConfig": {
                    "audioEncoding": self._audio_encoding,
                    "sampleRateHertz": self._sample_rate_hertz,
                },
            }

            _LOGGER.debug(
                'Getting TTS audio for message "%s" with configuration: %s',
                message[:50] + "..." if len(message) > 50 else message,
                payload,
            )

        except ValueError as err:
            _LOGGER.error("Configuration error: %s", err)
            raise Exception(f"Configuration error: {err}") from err

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._make_request, url, headers, payload
            )

            result = response.json()
            audio_content = base64.b64decode(result["audioContent"])

            _LOGGER.debug(
                "Successfully received TTS audio (%d bytes)", len(audio_content)
            )

            # Map audio encoding to proper format and extension
            encoding = self._audio_encoding.upper()
            if encoding == "MP3":
                return ("mp3", audio_content)
            elif encoding == "LINEAR16":
                return ("wav", audio_content)
            elif encoding == "OGG_OPUS":
                return ("opus", audio_content)
            elif encoding in ["ALAW", "MULAW"]:
                return ("wav", audio_content)
            else:
                # Default to mp3
                return ("mp3", audio_content)

        except requests.exceptions.HTTPError as err:
            _LOGGER.error("HTTP error from Inworld API: %s", err)
            if err.response.status_code == 401:
                raise Exception("Invalid API key") from err
            elif err.response.status_code == 429:
                raise Exception("Rate limit exceeded") from err
            else:
                raise Exception(
                    f"HTTP {err.response.status_code}: {err.response.text}"
                ) from err
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Request error to Inworld API: %s", err)
            raise Exception("Unable to connect to Inworld API") from err
        except Exception as err:
            _LOGGER.error("Unexpected error from Inworld API: %s", err)
            raise Exception("Unexpected error processing TTS request") from err

    def _make_request(
        self, url: str, headers: dict, payload: dict
    ) -> requests.Response:
        """Make synchronous request to Inworld API."""
        response = requests.post(
            url, json=payload, headers=headers, timeout=DEFAULT_API_TIMEOUT
        )
        response.raise_for_status()
        return response
