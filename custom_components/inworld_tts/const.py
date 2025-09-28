"""Constants for the Inworld TTS integration."""

from enum import Enum

TITLE = "Inworld TTS"
DOMAIN = "inworld_tts"

# Default Configuration
DEFAULT_API_BASE_URL = "https://api.inworld.ai/"
DEFAULT_API_TIMEOUT = 30
DEFAULT_AUDIO_ENCODING = "mp3"
DEFAULT_MODEL_ID = "inworld-tts-1"
DEFAULT_SAMPLE_RATE_HERTZ = 48000
DEFAULT_TEMPERATURE = 0.8
DEFAULT_TIMESTAMP_TYPE = "TIMESTAMP_TYPE_UNSPECIFIED"


# Available options
class SupportedAudioEncodings(Enum):
    """Supported audio encodings."""

    LINEAR16 = (
        "Uncompressed 16-bit signed little-endian samples (Linear PCM). Audio content returned as LINEAR16 also contains a WAV header.",
        "audio/wav",
    )
    MP3 = ("MP3 audio.", "audio/mpeg")
    OGG_OPUS = (
        "Opus encoded audio wrapped in an ogg container. The result will be a file which can be played natively on Android, and in browsers (at least Chrome and Firefox). The quality of the encoding is considerably higher than MP3 while using approximately the same bitrate.",
        "audio/opus",
    )
    ALAW = ("ALAW encoded audio. 8-bit companded PCM.", "audio/wav")
    MULAW = ("MULAW encoded audio. 8-bit companded PCM.", "audio/wav")

    def __init__(self, description: str, content_type: str):
        self.description = description
        self.content_type = content_type


SUPPORTED_MODEL_IDS = {
    "inworld-tts-1": "Inworld TTS (Fast, cost-efficient)",
    "inworld-tts-1-max": "Inworld TTS Max (More expressive, preview)",
}

SUPPORTED_TIMESTAMP_TYPES = {
    "TIMESTAMP_TYPE_UNSPECIFIED": "None",
    "WORD": "Word-level alignment",
    "CHARACTER": "Character-level alignment",
}
