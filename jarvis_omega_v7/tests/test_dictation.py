"""Unit tests for local-only dictation configuration and upload validation."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from types import SimpleNamespace
from core.dictation import ALLOWED_SUFFIXES, _run_transcription, configured_model_dir, get_status


class DictationConfigTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"GENESIS_WHISPER_MODEL_DIR": temp}):
                status = get_status()
        self.assertFalse(status.available)
        self.assertIn("model.bin", status.reason)

    def test_audio_extensions_are_explicit(self):
        self.assertIn(".wav", ALLOWED_SUFFIXES)
        self.assertIn(".webm", ALLOWED_SUFFIXES)
        self.assertNotIn(".exe", ALLOWED_SUFFIXES)

    def test_model_path_resolves_from_environment(self):
        with patch.dict(os.environ, {"GENESIS_WHISPER_MODEL_DIR": "C:/models/whisper"}):
            self.assertEqual(str(configured_model_dir()), "C:/models/whisper")

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
