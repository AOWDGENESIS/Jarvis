"""Unit tests for local-only dictation configuration and upload validation."""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.dictation import (
    ALLOWED_SUFFIXES,
    DictationStatus,
    _run_transcription,
    configured_model_dir,
    get_status,
    origin_matches_request,
    router,
)


class DictationConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    def test_missing_model_setting_is_unavailable_without_download(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GENESIS_WHISPER_MODEL_DIR", None)
            status = get_status()
        self.assertFalse(status.available)
        self.assertTrue(status.local_only)
        self.assertIn("no model will be downloaded", status.reason)

    def test_missing_directory_is_unavailable(self):
        with patch.dict(os.environ, {"GENESIS_WHISPER_MODEL_DIR": "Z:/definitely-not-a-model"}):
            status = get_status()
        self.assertFalse(status.available)
        self.assertIn("does not exist", status.reason)

    def test_model_directory_requires_model_bin(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"GENESIS_WHISPER_MODEL_DIR": temp}):
            status = get_status()
        self.assertFalse(status.available)
        self.assertIn("model.bin", status.reason)

    def test_origin_guard_allows_same_origin_and_non_browser_clients(self):
        self.assertTrue(origin_matches_request("http://127.0.0.1:8000", "http://127.0.0.1:8000/api/dictation/transcribe"))
        self.assertTrue(origin_matches_request(None, "http://127.0.0.1:8000/api/dictation/transcribe"))
        self.assertFalse(origin_matches_request("https://example.com", "http://127.0.0.1:8000/api/dictation/transcribe"))
        self.assertFalse(origin_matches_request("http://127.0.0.1:8001", "http://127.0.0.1:8000/api/dictation/transcribe"))
        self.assertFalse(origin_matches_request("https://evil.example", "https://evil.example/api/dictation/transcribe"))

    def test_audio_extensions_are_explicit(self):
        self.assertIn(".wav", ALLOWED_SUFFIXES)
        self.assertIn(".webm", ALLOWED_SUFFIXES)
        self.assertNotIn(".exe", ALLOWED_SUFFIXES)

    def test_model_path_resolves_from_environment(self):
        with patch.dict(os.environ, {"GENESIS_WHISPER_MODEL_DIR": "C:/models/whisper"}):
            self.assertEqual(str(configured_model_dir()), "C:/models/whisper")

    def test_endpoint_rejects_cross_origin_upload(self):
        response = self.client.post(
            "/api/dictation/transcribe",
            headers={"Origin": "https://example.com"},
            files={"audio": ("speech.webm", b"audio", "audio/webm")},
        )
        self.assertEqual(response.status_code, 403)

    def test_endpoint_rejects_unsupported_extension(self):
        response = self.client.post(
            "/api/dictation/transcribe",
            files={"audio": ("payload.exe", b"not audio", "application/octet-stream")},
        )
        self.assertEqual(response.status_code, 415)

    def test_endpoint_transcribes_with_existing_local_model(self):
        class FakeModel:
            def transcribe(self, path, **kwargs):
                return [SimpleNamespace(text=" Guten Tag. ")], SimpleNamespace(language="de", duration=1.0)

        ready = DictationStatus(available=True, model_dir="/existing/model", reason="ready")
        with patch("core.dictation.get_status", return_value=ready), patch("core.dictation._get_model", return_value=FakeModel()):
            response = self.client.post(
                "/api/dictation/transcribe?language=de",
                files={"audio": ("speech.webm", b"fake audio bytes", "audio/webm")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["text"], "Guten Tag.")
        self.assertTrue(response.json()["local_only"])

    def test_endpoint_returns_422_when_no_speech_is_recognized(self):
        class SilentModel:
            def transcribe(self, path, **kwargs):
                return [], SimpleNamespace(language="de", duration=0.5)

        ready = DictationStatus(available=True, model_dir="/existing/model", reason="ready")
        with patch("core.dictation.get_status", return_value=ready), patch("core.dictation._get_model", return_value=SilentModel()):
            response = self.client.post(
                "/api/dictation/transcribe",
                files={"audio": ("silence.webm", b"fake audio bytes", "audio/webm")},
            )
        self.assertEqual(response.status_code, 422)
        self.assertIn("No speech", response.json()["detail"])

    def test_endpoint_rejects_unsupported_language_before_model_load(self):
        with patch("core.dictation._get_model") as model_loader:
            response = self.client.post(
                "/api/dictation/transcribe?language=xx",
                files={"audio": ("speech.webm", b"fake audio bytes", "audio/webm")},
            )
        self.assertEqual(response.status_code, 400)
        model_loader.assert_not_called()

    def test_transcription_joins_nonempty_segments_and_uses_auto_language(self):
        class FakeModel:
            def transcribe(self, path, **kwargs):
                self.kwargs = kwargs
                segments = [SimpleNamespace(text=" Hallo "), SimpleNamespace(text=""), SimpleNamespace(text="Welt.")]
                return segments, SimpleNamespace(language="de", duration=1.25)

        model = FakeModel()
        result = _run_transcription(model, "unused.wav", "auto")
        self.assertEqual(result["text"], "Hallo Welt.")
        self.assertEqual(result["language"], "de")
        self.assertEqual(result["segments"], 2)
        self.assertIsNone(model.kwargs["language"])
        self.assertTrue(result["local_only"])


if __name__ == "__main__":
    unittest.main()
