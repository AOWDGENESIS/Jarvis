"""Local-only Whisper dictation API for JARVIS.

The engine never downloads a model. Set GENESIS_WHISPER_MODEL_DIR to an already
installed faster-whisper/CTranslate2 model directory before starting JARVIS.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

log = logging.getLogger("jarvis.dictation")
router = APIRouter(tags=["local-dictation"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024
ALLOWED_SUFFIXES = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".mp4", ".mpeg", ".mpga"}
_MODEL_LOCK = threading.Lock()
_MODEL: Any = None
_MODEL_PATH: str | None = None


class DictationStatus(BaseModel):
    available: bool
    local_only: bool = True
    model_dir: str | None = None
    reason: str


def configured_model_dir() -> Path | None:
    value = os.environ.get("GENESIS_WHISPER_MODEL_DIR", "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def get_status() -> DictationStatus:
    model_dir = configured_model_dir()
    if model_dir is None:
        return DictationStatus(
            available=False,
            reason="GENESIS_WHISPER_MODEL_DIR is not set; no model will be downloaded.",
        )
    if not model_dir.is_dir():
        return DictationStatus(
            available=False,
            model_dir=str(model_dir),
            reason="Configured local model directory does not exist; no model will be downloaded.",
        )
    required_files = ("model.bin", "config.json", "tokenizer.json", "vocabulary.json")
    missing = [name for name in required_files if not (model_dir / name).is_file()]
    if missing:
        return DictationStatus(
            available=False,
            model_dir=str(model_dir),
            reason="Local model directory is incomplete; missing: " + ", ".join(missing),
        )
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return DictationStatus(
            available=False,
            model_dir=str(model_dir),
            reason="faster-whisper is not installed in the active Python environment.",
        )
    return DictationStatus(
        available=True,
        model_dir=str(model_dir),
        reason="Local model files found; inference stays on this machine.",
    )


def _get_model() -> Any:
    global _MODEL, _MODEL_PATH
    status = get_status()
    if not status.available or not status.model_dir:
        raise RuntimeError(status.reason)
    with _MODEL_LOCK:
        if _MODEL is not None and _MODEL_PATH == status.model_dir:
            return _MODEL
        from faster_whisper import WhisperModel
        device = os.environ.get("GENESIS_WHISPER_DEVICE", "auto").strip() or "auto"
        compute_type = os.environ.get("GENESIS_WHISPER_COMPUTE_TYPE", "default").strip() or "default"
        # local_files_only is deliberate: startup must never fetch model data.
        _MODEL = WhisperModel(
            status.model_dir,
            device=device,
            compute_type=compute_type,
            local_files_only=True,
        )
        _MODEL_PATH = status.model_dir
        return _MODEL


@router.get("/api/dictation/status", response_model=DictationStatus)
async def dictation_status() -> DictationStatus:
    return get_status()


@router.post("/api/dictation/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), language: str = "de") -> dict[str, Any]:
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Unsupported audio extension.")
    status = get_status()
    if not status.available:
        raise HTTPException(status_code=503, detail=status.reason)

    temp_path: str | None = None
    try:
        total = 0
        with tempfile.NamedTemporaryFile(prefix="jarvis-dictation-", suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    raise HTTPException(status_code=413, detail="Audio exceeds the 25 MiB limit.")
                tmp.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty.")

        model = _get_model()
        selected_language = language.strip().lower() or "de"
        if selected_language not in {"de", "en", "fr", "es", "it", "nl", "pl", "auto"}:
            raise HTTPException(status_code=400, detail="Unsupported language code.")
        segments, info = await run_in_threadpool(
            model.transcribe,
            temp_path,
            language=None if selected_language == "auto" else selected_language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
        )
        parts = []
        for segment in segments:
            text = (segment.text or "").strip()
            if text:
                parts.append(text)
        transcript = " ".join(parts).strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="No speech could be recognized.")
        return {
            "text": transcript,
            "language": getattr(info, "language", selected_language),
            "duration": getattr(info, "duration", None),
            "segments": len(parts),
            "engine": "faster-whisper",
            "local_only": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Local dictation failed")
        raise HTTPException(status_code=500, detail="Local transcription failed; see JARVIS log.") from exc
    finally:
        await audio.close()
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                log.warning("Could not remove temporary dictation audio file: %s", temp_path)
