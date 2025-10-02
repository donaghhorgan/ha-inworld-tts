"""Support for Inworld TTS service."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import aiohttp
from homeassistant.components.tts import (
    TextToSpeechEntity,
    TtsAudioType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_AUDIO_ENCODING,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL_ID,
    DEFAULT_SAMPLE_RATE_HERTZ,
    DEFAULT_TEMPERATURE,
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
        # Check options first (for user-configurable settings), then data (for setup settings)
        if key in self._config_entry.options:
            return self._config_entry.options[key]
        elif key in self._config_entry.data:
            return self._config_entry.data[key]
        else:
            if default is not None:
                return default
            raise ValueError(f"Required configuration '{key}' is not set")

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
        return self._get_config_value("voice_id", "")

    @property
    def _model_id(self) -> str:
        """Get model ID from config."""
        return self._get_config_value("model_id", DEFAULT_MODEL_ID)

    @property
    def _language(self) -> str:
        """Get language from config."""
        return self._get_config_value("language", DEFAULT_LANGUAGE)

    @property
    def _audio_encoding(self) -> str:
        """Get audio encoding from config."""
        return self._get_config_value("audio_encoding", DEFAULT_AUDIO_ENCODING)

    @property
    def _sample_rate_hertz(self) -> int:
        """Get sample rate from config."""
        return self._get_config_value("sample_rate_hertz", DEFAULT_SAMPLE_RATE_HERTZ)

    @property
    def _temperature(self) -> float:
        """Get temperature from config."""
        return self._get_config_value("temperature", DEFAULT_TEMPERATURE)

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return [self._language]

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
        return {"voice": self._get_config_value("voice_id", "")}

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> TtsAudioType:
        """Load TTS from Inworld using streaming API."""
        try:
            if language != self._language:
                raise Exception(f"Language '{language}' not supported")

            # Get voice from options if provided, otherwise use default
            voice_id = self._voice_id
            if options and "voice" in options:
                voice_id = options["voice"]

            url = f"{self._api_url}/tts/v1/voice:stream"
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
            audio_content = await self._make_streaming_request(url, headers, payload)

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

        except aiohttp.ClientResponseError as err:
            _LOGGER.error("HTTP error from Inworld API: %s", err)
            if err.status == 401:
                raise Exception("Invalid API key") from err
            elif err.status == 429:
                raise Exception("Rate limit exceeded") from err
            else:
                raise Exception(f"HTTP {err.status}: {err.message}") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Request error to Inworld API: %s", err)
            raise Exception("Unable to connect to Inworld API") from err
        except Exception as err:
            _LOGGER.error("Unexpected error from Inworld API: %s", err)
            raise Exception("Unexpected error processing TTS request") from err

    async def _make_streaming_request(
        self, url: str, headers: dict, payload: dict
    ) -> bytes:
        """Make streaming request to Inworld API and collect audio chunks."""
        audio_chunks = []

        timeout = aiohttp.ClientTimeout(total=DEFAULT_API_TIMEOUT)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(url, json=payload, headers=headers) as response,
        ):
            response.raise_for_status()

            # Read streaming response line by line
            async for line in response.content:
                if line.strip():  # Skip empty lines
                    try:
                        # Parse JSON response chunk
                        chunk_data = json.loads(line.decode("utf-8"))

                        # Check for errors in the stream
                        if "error" in chunk_data:
                            error_msg = chunk_data["error"].get(
                                "message", "Unknown error"
                            )
                            raise Exception(f"API error: {error_msg}")

                        # Extract audio content from result
                        if (
                            "result" in chunk_data
                            and "audioContent" in chunk_data["result"]
                        ):
                            audio_b64 = chunk_data["result"]["audioContent"]
                            audio_bytes = base64.b64decode(audio_b64)
                            audio_chunks.append(audio_bytes)

                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
                    except Exception as e:
                        _LOGGER.error("Error processing audio chunk: %s", e)
                        raise

        # Combine all audio chunks
        return b"".join(audio_chunks)
