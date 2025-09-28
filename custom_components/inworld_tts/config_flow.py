"""Config flow for Inworld TTS integration."""

from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DEFAULT_API_BASE_URL,
    DEFAULT_AUDIO_ENCODING,
    DEFAULT_MODEL_ID,
    DEFAULT_SAMPLE_RATE_HERTZ,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMESTAMP_TYPE,
    DOMAIN,
    SUPPORTED_MODEL_IDS,
    SUPPORTED_TIMESTAMP_TYPES,
    TITLE,
    SupportedAudioEncodings,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_connection_and_fetch_voices(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, list[dict[str, str]]]:
    """Validate the API connection and fetch available voices organized by language."""
    api_url = data.get("api_url", DEFAULT_API_BASE_URL).rstrip("/")
    api_key = data["api_key"]

    url = f"{api_url}/tts/v1/voices"
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = await hass.async_add_executor_job(requests.get, url, None, headers)
        response.raise_for_status()
        response_data = response.json()

        # Organize voices by language
        voices_by_language: dict[str, list[dict[str, str]]] = {}
        for voice in response_data.get("voices", []):
            for language in voice.get("languages", []):
                if language not in voices_by_language:
                    voices_by_language[language] = []
                voices_by_language[language].append(
                    {
                        "value": voice["voiceId"],
                        "label": voice.get("displayName") or voice["voiceId"],
                    }
                )

        return voices_by_language
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            raise InvalidAuth from err
        else:
            raise CannotConnect from err
    except requests.exceptions.RequestException as err:
        raise CannotConnect from err


async def validate_voice_input(
    hass: HomeAssistant, data: dict[str, Any], api_data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the voice configuration by making a test TTS call."""
    url = f"{api_data['api_url']}/tts/v1/voice:stream"
    headers = {
        "Authorization": f"Basic {api_data['api_key']}",
        "Content-Type": "application/json",
    }
    # Build payload with all configuration options
    payload = {"text": "Test", "voiceId": data["voice_id"], "modelId": data["model_id"]}

    # Add optional configuration if provided
    if "temperature" in data:
        payload["temperature"] = data["temperature"]

    if "timestamp_type" in data:
        payload["timestampType"] = data["timestamp_type"]

    # Add audio config if audio encoding or sample rate specified
    audio_config = {}
    if "sample_rate_hertz" in data:
        audio_config["sampleRateHertz"] = data["sample_rate_hertz"]

    if "audio_encoding" in data:
        audio_config["audioEncoding"] = SupportedAudioEncodings[
            data.get("audioEncoding", DEFAULT_AUDIO_ENCODING).upper()
        ].name

    if audio_config:
        payload["audioConfig"] = audio_config

    try:
        response = await hass.async_add_executor_job(
            requests.post, url, payload, headers
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            raise InvalidAuth from err
        else:
            raise CannotConnect from err
    except requests.exceptions.RequestException as err:
        raise CannotConnect from err

    return {"title": TITLE}


class InworldTTSConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Inworld TTS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_data: dict[str, Any] = {}
        self._voices_by_language: dict[str, list[dict[str, str]]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - API configuration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                # Validate connection and fetch voices in one call
                self._voices_by_language = (
                    await validate_api_connection_and_fetch_voices(
                        self.hass, user_input
                    )
                )
                self._api_data = user_input
                return await self.async_step_voice()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("api_url", default=DEFAULT_API_BASE_URL): str,
                    vol.Required("api_key"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_voice(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the voice selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_voice_input(self.hass, user_input, self._api_data)
                return self.async_create_entry(
                    title=TITLE, data={**self._api_data, **user_input}
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Build language options
        language_options = [
            {"value": lang, "label": lang.upper()}
            for lang in sorted(self._voices_by_language.keys())
        ]

        # Build voice options (initially empty, will be populated via frontend)
        voice_options = []
        if self._voices_by_language:
            # Show voices for the first language as default
            first_lang = sorted(self._voices_by_language.keys())[0]
            voice_options = self._voices_by_language[first_lang]

        # Create dynamic schema with selectors
        data_schema = vol.Schema(
            {
                vol.Required("language"): vol.In(
                    {opt["value"]: opt["label"] for opt in language_options}
                ),
                vol.Required("voice_id"): vol.In(
                    {opt["value"]: opt["label"] for opt in voice_options}
                ),
                vol.Optional("model_id", default=DEFAULT_MODEL_ID): vol.In(
                    SUPPORTED_MODEL_IDS
                ),
                vol.Optional("audio_encoding", default=DEFAULT_AUDIO_ENCODING): vol.In(
                    SupportedAudioEncodings._member_map_.keys()
                ),
                vol.Optional(
                    "sample_rate_hertz", default=DEFAULT_SAMPLE_RATE_HERTZ
                ): vol.All(int, vol.Range(min=8000, max=48000)),
                vol.Optional("temperature", default=DEFAULT_TEMPERATURE): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=2.0)
                ),
                vol.Optional(
                    "timestamp_type",
                    default=DEFAULT_TIMESTAMP_TYPE,
                ): vol.In(SUPPORTED_TIMESTAMP_TYPES),
            }
        )

        return self.async_show_form(
            step_id="voice",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "voices_data": str(self._voices_by_language),
            },
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
