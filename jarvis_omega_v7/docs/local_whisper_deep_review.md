# Deep-Review-Report: Local Whisper dictation integration

- Review basis: `AI-Deep-Review-Prompt-Pack` German master prompt, version 1.2.2 (2026-09-30).
- Scope: new local dictation router, JARVIS startup integration, voice-bar UI changes, dependencies, unit tests, and CI workflow.
- Activated profiles: universal core, Python, FastAPI/HTTP API, browser JavaScript/media capture, dependency and CI review.
- Evidence labels follow the master prompt: BELEGT, PLAUSIBEL, ANNAHME, NICHT_VERIFIZIERBAR.
- Review mode: source review plus GitHub Actions compile/unit-test checks. No Windows runtime, microphone, or local model was available to this review.

## 1. Architecture and trust boundaries

Browser voice bar -> same-origin JARVIS API -> upload size/extension/origin checks -> temporary audio file -> pre-existing local faster-whisper model -> transcript returned to the browser command field for user review.

The new feature does not send dictation audio to Ollama or a remote speech service. Model loading uses `local_files_only=True`; the model directory must already exist.

## 2. Findings

### [DR-001] INFO Existing JARVIS has other network-enabled features
- Category: privacy boundary / scope
- Location: `core/voice.py` (`EdgeTTSEngine`); `main.py` routes `/api/worldnews`, `/api/version`, and `/api/models/pull`.
- Evidence: the existing Edge TTS engine uses the `edge_tts` package; world-news and version routes use remote URLs; model-pull route starts `ollama pull`.
- Cause and impact: the *new dictation path* is local-only, but the full existing JARVIS application is not wholly offline by default.
- Reproduction/test idea: inspect those routes and test JARVIS with outbound network blocked.
- Minimal fix: if strict offline operation is required, add a separate global offline mode that disables remote TTS, news/version requests, and model-pull actions, then test each route.
- Regression test: network-disabled test profile verifies that dictation still works and remote features are disabled or clearly report unavailable.
- References: `jarvis_omega_v7/core/voice.py`, `jarvis_omega_v7/main.py`.
- Evidence status: BELEGT
- Confidence: HIGH

### [DR-002] INFO A local Whisper model must be configured and preinstalled
- Category: configuration / deployment
- Location: `core/dictation.py`, `configured_model_dir()`, `get_status()`.
- Evidence: the feature requires `GENESIS_WHISPER_MODEL_DIR` and local model files; absent or incomplete configuration makes the API unavailable rather than downloading a model.
- Cause and impact: without an existing compatible model and the environment variable, the W control reports that dictation is not ready and the endpoint returns 503.
- Reproduction/test idea: run the unit tests for unset, missing, and incomplete model paths.
- Minimal fix: set the variable to the actual local faster-whisper model directory in the JARVIS launcher after verifying that model already exists.
- Regression test: startup status remains unavailable when model files are absent; no download is attempted.
- References: `jarvis_omega_v7/docs/local_whisper_dictation.md`.
- Evidence status: BELEGT
- Confidence: HIGH

### [DR-003] LOW File presence is not proof that a model is loadable
- Category: error handling / deployment integrity
- Location: `core/dictation.py`, `get_status()` and `_get_model()`.
- Evidence: status verifies required filenames; actual model loading occurs on first transcription.
- Cause and impact: corrupt, incompatible, or internally inconsistent model files can pass the status check but fail on first use, returning a generic 500 response and a server-side diagnostic.
- Minimal fix: keep the current lazy load to avoid loading a large model during JARVIS startup, but add an optional explicit model self-test that loads and unloads the model under operator control.
- Regression test: inject an invalid model directory and confirm the API returns a controlled error and cleans up the temporary audio.
- References: `jarvis_omega_v7/core/dictation.py`.
- Evidence status: BELEGT
- Confidence: HIGH

### [DR-004] INFO End-to-end Windows audio behavior remains unverified
- Category: testing / compatibility
- Location: browser MediaRecorder UI and `/api/dictation/transcribe`.
- Evidence: CI compiles Python modules and runs unit tests with a fake transcription model; it does not capture microphone audio or load a real Whisper model.
- Impact: browser MIME support, Windows audio devices, actual model compatibility, CUDA behavior, and German transcription quality are not proven by CI.
- Minimal fix: perform a local Windows acceptance test with the installed model, and record device, model path, language, and results in a compact diagnostic report.
- Regression test: record a short German sentence, verify transcript content, then repeat with no model configured and with an unsupported file extension.
- Evidence status: BELEGT
- Confidence: HIGH

## 3. Positively verified safeguards

- Model download is not initiated by the new feature; model loading requests `local_files_only=True`.
- Upload size is limited to 25 MiB and file extensions are allow-listed.
- Browser requests with a different Origin are rejected; non-browser clients without Origin remain supported.
- Temporary audio is removed in a `finally` block.
- Inference runs in a worker thread and is serialized against the shared model.
- The transcript is inserted into the input field and is not automatically sent as a JARVIS command.
- Existing browser speech recognition is preserved.
- CI checks Python compilation and automated unit tests.

## 4. Verification record

- GitHub Actions workflow: `.github/workflows/local-dictation-checks.yml`.
- Confirmed completed successful run before the final Origin/MIME refinements: compile step PASS and unit-test step PASS.
- Latest Origin-guard and MIME refinements are being checked by the workflow on the branch; their final run must be green before this PR is considered validated.
- No merge, release, or deployment was performed.
- Local Windows acceptance remains open and cannot be inferred from GitHub CI.

## 5. Prioritized next steps

1. Wait for CI on the final branch head and resolve any failure.
2. Run Windows acceptance tests with the user's actual JARVIS Python environment and an already-installed model.
3. If the goal is strict offline JARVIS, separately gate the pre-existing remote TTS/news/version/model-download features.
4. Keep the pull request in draft until local acceptance evidence is recorded.
