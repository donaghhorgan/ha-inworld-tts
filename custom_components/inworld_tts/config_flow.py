"""Config flow for Inworld TTS integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DEFAULT_API_BASE_URL,
    DEFAULT_API_TIMEOUT,
    DEFAULT_AUDIO_ENCODING,
    DEFAULT_MODEL_ID,
    DEFAULT_SAMPLE_RATE_HERTZ,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    SUPPORTED_MODEL_IDS,
    TITLE,
    SupportedAudioEncodings,
)

_LOGGER = logging.getLogger(__name__)


async def get_voices_and_languages(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, list[dict[str, str]]]:
    """Fetch available voices organized by language."""
    api_url = data.get("api_url", DEFAULT_API_BASE_URL).rstrip("/")
    api_key = data["api_key"]

    url = f"{api_url}/tts/v1/voices"
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_API_TIMEOUT)
            ) as session,
            session.get(url, headers=headers) as response,
        ):
            response.raise_for_status()
            response_data = await response.json()

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
    except aiohttp.ClientResponseError as err:
        if err.status == 401:
            raise InvalidAuth from err
        else:
            raise CannotConnect from err
    except aiohttp.ClientError as err:
        raise CannotConnect from err


class InworldTTSConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Inworld TTS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        pass

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - API configuration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                # Just validate the API connection
                await get_voices_and_languages(self.hass, user_input)
                return self.async_create_entry(title=TITLE, data=user_input)
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

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:  # noqa: ARG004
        """Create the options flow."""
        return InworldTTSOptionsFlow()


class InworldTTSOptionsFlow(OptionsFlow):
    """Handle options flow for Inworld TTS."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        super().__init__()
        self._voices_by_language: dict[str, list[dict[str, str]]] = {}
        self._selected_language: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial options step - voice and advanced configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # If language changed, update selected language and re-show form
            if "language" in user_input:
                new_language = user_input["language"]
                if new_language != self._selected_language:
                    self._selected_language = new_language
                    # If only language field provided or voice_id not valid for new language
                    if (
                        "voice_id" not in user_input
                        or new_language not in self._voices_by_language
                        or not any(
                            voice["value"] == user_input.get("voice_id")
                            for voice in self._voices_by_language[new_language]
                        )
                    ):
                        return await self._show_options_form(errors)

            # Validate complete form submission
            try:
                await validate_voice_input(
                    self.hass, user_input, dict(self.config_entry.data)
                )
                return self.async_create_entry(title="", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Fetch voices on first load
        if not self._voices_by_language:
            try:
                self._voices_by_language = await get_voices_and_languages(
                    self.hass, dict(self.config_entry.data)
                )
            except Exception:
                _LOGGER.exception("Failed to fetch voices")
                errors["base"] = "cannot_connect"

        return await self._show_options_form(errors)

    async def _show_options_form(self, errors: dict[str, str]) -> ConfigFlowResult:
        """Show the options form with voice and advanced configuration."""
        # Get current options with defaults
        current_options = self.config_entry.options

        # Build language options
        language_options = {
            lang: lang.upper() for lang in sorted(self._voices_by_language.keys())
        }

        # Build voice options based on selected language
        voice_options = {}
        selected_language = self._selected_language or current_options.get("language")

        if not selected_language and self._voices_by_language:
            # Default to first language if none selected
            selected_language = sorted(self._voices_by_language.keys())[0]
            self._selected_language = selected_language

        if selected_language and selected_language in self._voices_by_language:
            voice_options = {
                opt["value"]: opt["label"]
                for opt in self._voices_by_language[selected_language]
            }

        # Create schema with current selections or defaults
        data_schema_dict = {
            vol.Required("language", default=selected_language): vol.In(
                language_options
            ),
            vol.Optional(
                "model_id", default=current_options.get("model_id", DEFAULT_MODEL_ID)
            ): vol.In(SUPPORTED_MODEL_IDS),
            vol.Optional(
                "audio_encoding",
                default=current_options.get("audio_encoding", DEFAULT_AUDIO_ENCODING),
            ): vol.In(SupportedAudioEncodings._member_map_.keys()),
            vol.Optional(
                "sample_rate_hertz",
                default=current_options.get(
                    "sample_rate_hertz", DEFAULT_SAMPLE_RATE_HERTZ
                ),
            ): vol.All(int, vol.Range(min=8000, max=48000)),
            vol.Optional(
                "temperature",
                default=current_options.get("temperature", DEFAULT_TEMPERATURE),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        }

        # Add voice_id field only if we have voices for the selected language
        if voice_options:
            current_voice = current_options.get("voice_id", "")
            # Use current voice if it's valid for the selected language, otherwise use first available
            default_voice = (
                current_voice
                if current_voice in voice_options
                else list(voice_options.keys())[0]
                if voice_options
                else ""
            )
            data_schema_dict[vol.Required("voice_id", default=default_voice)] = vol.In(
                voice_options
            )
        else:
            data_schema_dict[
                vol.Optional("voice_id", default=current_options.get("voice_id", ""))
            ] = str

        data_schema = vol.Schema(data_schema_dict)

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "voices_data": str(self._voices_by_language),
                "selected_language": selected_language or "",
            },
        )


async def validate_voice_input(
    hass: HomeAssistant, data: dict[str, Any], api_data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the voice configuration by making a test TTS call."""
    api_url = api_data.get("api_url", DEFAULT_API_BASE_URL).rstrip("/")
    api_key = api_data["api_key"]

    url = f"{api_url}/tts/v1/voice"
    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json",
    }
    # Build payload with all configuration options
    payload = {"text": "Test", "voiceId": data["voice_id"], "modelId": data["model_id"]}

    # Add optional configuration if provided
    if "temperature" in data:
        payload["temperature"] = data["temperature"]

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
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_API_TIMEOUT)
            ) as session,
            session.post(url, json=payload, headers=headers) as response,
        ):
            response.raise_for_status()
    except aiohttp.ClientResponseError as err:
        if err.status == 401:
            raise InvalidAuth from err
        else:
            raise CannotConnect from err
    except aiohttp.ClientError as err:
        raise CannotConnect from err

    return {"title": TITLE}


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
