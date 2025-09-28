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
    SupportedAudioEncodings,
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
        self._api_url = config_entry.data["api_url"]
        self._api_key = config_entry.data["api_key"]
        self._voice_id = config_entry.data["voice_id"]
        self._model_id = config_entry.data["model_id"]
        self._language = config_entry.data["language"]
        self._audio_encoding = config_entry.data["audio_encoding"]
        self._sample_rate_hertz = config_entry.data["sample_rate_hertz"]
        self._temperature = config_entry.data["temperature"]
        self._timestamp_type = config_entry.data["timestamp_type"]

        self._attr_name = TITLE
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}"

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return [self._language]

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return self._language

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Load TTS from Inworld."""
        if language != self._language:
            raise Exception(f"Language '{language}' not supported")

        url = f"{self._api_url}/tts/v1/voice:stream"
        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

        # Prepare audio config based on format
        payload = {
            "text": message,
            "voiceId": self._voice_id,
            "modelId": self._model_id,
            "temperature": self._temperature,
            "audioConfig": {
                "audioEncoding": self._audio_encoding,
                "sampleRateHertz": self._sample_rate_hertz,
            },
            "timestampType": self._timestamp_type,
        }

        content_type = SupportedAudioEncodings[
            self._audio_encoding.upper()
        ].content_type

        _LOGGER.debug(
            'Getting TTS audio for message "%s" with configuration: %s',
            message[:50] + "..." if len(message) > 50 else message,
            payload,
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._make_request, url, headers, payload
            )

            result = response.json()
            audio_content = base64.b64decode(result["audioContent"])

            _LOGGER.debug(
                "Successfully received TTS audio (%d bytes)", len(audio_content)
            )

            return (content_type, audio_content)

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
