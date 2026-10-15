# Local Whisper dictation for JARVIS

This feature adds a separate local transcription path to the existing JARVIS web interface. The existing browser speech recognition remains available.

## Privacy and model setup

- The API is served by the existing JARVIS process on its loopback address.
- The endpoint accepts audio uploads up to 25 MiB and a fixed allowlist of audio extensions.
- The server never downloads a model. It uses only an existing faster-whisper/CTranslate2 model directory.
- Audio is written to a temporary file for inference and removed afterward.
- The new feature does not call Ollama or any external speech API.

Before starting JARVIS, set `GENESIS_WHISPER_MODEL_DIR` to an existing model directory. That directory must contain `model.bin`, `config.json`, `tokenizer.json`, and `vocabulary.json`. The model must already be present on disk. For example, in PowerShell for the current session:

```powershell
$env:GENESIS_WHISPER_MODEL_DIR = 'F:\\Models\\faster-whisper-small'
```

The example is a path template, not a claim that a model is installed there. Use the actual directory on your machine. Optional settings:

- `GENESIS_WHISPER_DEVICE`: `auto` by default; can be `cpu` or a supported CUDA device.
- `GENESIS_WHISPER_COMPUTE_TYPE`: `default` by default; choose a value supported by your installed CTranslate2 build.

The UI's green `W` control checks `/api/dictation/status`, records audio using the browser, posts it to `/api/dictation/transcribe`, and places the result in the command field for review. It does not automatically send the recognized text.

## Validation

From `jarvis_omega_v7` with a Python environment that has FastAPI and python-multipart installed:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q core main.py
```

A successful unit-test run validates the configuration guards only. It does not prove microphone compatibility, model quality, CUDA availability, or end-to-end operation on another machine.
