# Inworld TTS for Home Assistant

A Home Assistant custom component that integrates with
[Inworld TTS](https://inworld.ai/tts) for high-quality, ultra-realistic
text-to-speech.

## Features

- High-quality speech synthesis using Inworld's TTS models
- Multiple voices and languages
- Audio formats: MP3, Linear PCM, Opus, μ-law, A-law
- Audio markups for emotions and non-verbal sounds
- Configurable temperature, sample rate, and model selection

## Installation

1. Copy the `inworld_tts` folder to your `custom_components` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "Inworld TTS" and enter your API key from [Inworld Platform](https://platform.inworld.ai/)

## Usage

Call the TTS service with your message:

```yaml
service: tts.speak
data:
  entity_id: tts.inworld_tts
  message: "Hello, this is Inworld TTS!"
```

Use audio markups for emotions and effects:

```yaml
service: tts.speak
data:
  entity_id: tts.inworld_tts
  message: "[happy] Great news! [sigh] But I'm tired."
```

## Configuration Options

The integration supports various audio formats (MP3, Linear PCM, Opus,
μ-law, A-law), multiple languages, and audio markups including:

- **Emotions**: `[happy]`, `[sad]`, `[angry]`, `[surprised]`, `[fearful]`, `[disgusted]`
- **Delivery**: `[laughing]`, `[whispering]`
- **Non-verbal**: `[breathe]`, `[cough]`, `[laugh]`, `[sigh]`, `[yawn]`

Advanced parameters like temperature (0.0-2.0) and sample rate
(8000-48000 Hz) can be configured during setup.

## Troubleshooting

- **Invalid API Key**: Verify your API key from the [Inworld Platform](https://platform.inworld.ai/)
- **Connection Issues**: Ensure Home Assistant can reach `api.inworld.ai`
- **Rate Limiting**: Check your usage limits on the Inworld Platform

Enable debug logging by adding this to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.inworld_tts: debug
```

## Development

### Setup

```bash
git clone https://github.com/donaghhorgan/ha-inworld-tts.git
cd ha-inworld-tts
uv sync --dev
uv run pre-commit install
```

### Available Commands

```bash
uv sync --dev                      # Install dependencies
uv run ruff format                 # Format code
uv run ruff check --fix            # Lint and fix
uv run mypy                        # Type checking
uv run bandit -r                   # Security scan
uv run pre-commit run --all-files  # Run all checks
```

The project uses pre-commit hooks for code quality, including formatting
(ruff), linting (mypy), and security scanning (bandit).

## Support

- **Integration Issues**: [GitHub Issues](https://github.com/donaghhorgan/ha-inworld-tts/issues)
- **API Issues**: [Inworld Support](https://inworld.ai/support)

## License

GPLv3 License
