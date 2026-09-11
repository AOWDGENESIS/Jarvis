"""
core/voice.py â€” JARVIS OMNI v7.6 OMEGA
E2/E6: Edge-TTS als primÃ¤re Stimme (klar, natÃ¼rlich, keine Stottern).
E4:    Backend spricht NICHT mehr direkt â€” /api/tts gibt Audio-Bytes zurÃ¼ck,
       das Frontend spielt ab. Nur EINE Audio-Quelle gleichzeitig.
Fallback: pyttsx3 wenn edge-tts nicht verfÃ¼gbar (kein Internet / Fehler).
"""
import asyncio
import io
import os
import logging
import queue
import threading
import time

log = logging.getLogger("jarvis.voice")

# â”€â”€ Deutsche Edge-TTS Stimmen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# VollstÃ¤ndige Liste â€” user wÃ¤hlt in Einstellungen
EDGE_VOICES_DE = [
    {"id": "de-DE-KatjaNeural",       "label": "Katja (â™€ Standard)",    "gender": "F"},
    {"id": "de-DE-ConradNeural",      "label": "Conrad (â™‚ Klar)",       "gender": "M"},
    {"id": "de-DE-KillianNeural",     "label": "Killian (â™‚ Tief)",      "gender": "M"},
    {"id": "de-DE-AmalaNeural",       "label": "Amala (â™€ Jung)",        "gender": "F"},
    {"id": "de-DE-LouisaNeural",      "label": "Louisa (â™€ Warm)",       "gender": "F"},
    {"id": "de-DE-BerndNeural",       "label": "Bernd (â™‚)",             "gender": "M"},
    {"id": "de-DE-ChristophNeural",   "label": "Christoph (â™‚)",         "gender": "M"},
    {"id": "de-DE-ElkeNeural",        "label": "Elke (â™€)",              "gender": "F"},
    {"id": "de-DE-KasperNeural",      "label": "Kasper (â™‚)",            "gender": "M"},
    {"id": "de-DE-KlarissaNeural",    "label": "Klarissa (â™€)",          "gender": "F"},
    {"id": "de-DE-KlausNeural",       "label": "Klaus (â™‚)",             "gender": "M"},
    {"id": "de-DE-MajaNeural",        "label": "Maja (â™€)",              "gender": "F"},
    {"id": "de-DE-RalfNeural",        "label": "Ralf (â™‚)",              "gender": "M"},
    {"id": "de-DE-SeraphinaNeural",   "label": "Seraphina (â™€)",         "gender": "F"},
    {"id": "de-DE-TanjaNeural",       "label": "Tanja (â™€)",             "gender": "F"},
    {"id": "de-AT-IngridNeural",      "label": "Ingrid (â™€ Ã–sterreich)", "gender": "F"},
    {"id": "de-AT-JonasNeural",       "label": "Jonas (â™‚ Ã–sterreich)",  "gender": "M"},
    {"id": "de-CH-LeniNeural",        "label": "Leni (â™€ Schweiz)",      "gender": "F"},
    {"id": "de-CH-JanNeural",         "label": "Jan (â™‚ Schweiz)",       "gender": "M"},
]

DEFAULT_VOICE = "de-DE-KatjaNeural"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EDGE-TTS ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class EdgeTTSEngine:
    """
    Generiert MP3-Bytes via Microsoft Edge-TTS.
    Wird NUR fÃ¼r /api/tts verwendet â€” Frontend spielt ab (E4-konform).
    """
    _available: bool | None = None  # None = noch nicht getestet

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import edge_tts  # noqa: F401
                self._available = True
            except ImportError:
                log.warning("[EdgeTTS] Package 'edge-tts' nicht installiert.")
                self._available = False
        return self._available

    async def synthesize_async(self, text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", volume: str = "+0%") -> bytes:
        """
        Gibt MP3-Bytes zurÃ¼ck oder leere Bytes bei Fehler.
        rate:   z.B. "+10%" = 10% schneller, "-5%" = langsamer
        volume: z.B. "+0%"  = normal
        """
        if not self.is_available():
            return b""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text   = text,
                voice  = voice,
                rate   = rate,
                volume = volume,
            )
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            audio = buf.getvalue()
            if not audio:
                log.warning("[EdgeTTS] Leere Audio-Antwort von Microsoft.")
            else:
                log.info(f"[EdgeTTS] âœ“ {len(audio)} Bytes generiert (Stimme: {voice})")
            return audio
        except Exception as e:
            log.error(f"[EdgeTTS] Synthese-Fehler: {e}")
            return b""




# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PIPER TTS ENGINE â€” A4: VollstÃ¤ndig lokal, kein Internet nÃ¶tig
# Installieren: INSTALL_PIPER.bat ausfÃ¼hren
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class PiperTTSEngine:
    """
    Lokal laufende Neural-TTS via Piper (rhasspy/piper).
    Generiert WAV-Bytes ohne Internetverbindung.
    PrioritÃ¤t: hÃ¶her als Edge-TTS wenn piper.exe vorhanden.
    """
    PIPER_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "piper")
    PIPER_EXE   = os.path.join(PIPER_DIR, "piper.exe")
    VOICES_DIR  = os.path.join(PIPER_DIR, "voices")
    DEFAULT_VOICE = "de_DE-thorsten-high"

    def is_available(self) -> bool:
        return os.path.isfile(self.PIPER_EXE)

    def get_voices(self) -> list:
        """Listet installierte Piper-Stimmen."""
        if not os.path.isdir(self.VOICES_DIR):
            return []
        return [
            f.replace(".onnx", "")
            for f in os.listdir(self.VOICES_DIR)
            if f.endswith(".onnx") and not f.endswith(".json")
        ]

    def synthesize(self, text: str, voice: str = None) -> bytes:
        """
        Generiert WAV-Bytes via piper.exe.
        Gibt leere Bytes zurÃ¼ck wenn piper nicht verfÃ¼gbar.
        """
        import subprocess, tempfile, io

        if not self.is_available():
            log.warning("[Piper] piper.exe nicht gefunden. INSTALL_PIPER.bat ausfÃ¼hren.")
            return b""

        voice_name = voice or self.DEFAULT_VOICE
        model_path = os.path.join(self.VOICES_DIR, f"{voice_name}.onnx")

        if not os.path.isfile(model_path):
            available = self.get_voices()
            if available:
                model_path = os.path.join(self.VOICES_DIR, f"{available[0]}.onnx")
                log.info(f"[Piper] Fallback auf: {available[0]}")
            else:
                log.warning("[Piper] Keine Stimmen installiert. INSTALL_PIPER.bat ausfÃ¼hren.")
                return b""

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            proc = subprocess.run(
                [self.PIPER_EXE, "--model", model_path,
                 "--output_file", tmp_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if proc.returncode != 0:
                log.error(f"[Piper] Fehler: {proc.stderr.decode('utf-8','ignore')[:200]}")
                return b""

            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()

            os.unlink(tmp_path)
            log.info(f"[Piper] âœ“ {len(wav_bytes)} Bytes WAV generiert (lokal, kein Internet)")
            return wav_bytes

        except subprocess.TimeoutExpired:
            log.error("[Piper] Timeout beim Generieren.")
            return b""
        except Exception as e:
            log.error(f"[Piper] Fehler: {e}")
            return b""

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PYTTSX3 FALLBACK ENGINE
# Wird nur noch als Fallback genutzt wenn edge-tts nicht verfÃ¼gbar.
# Spricht direkt (fÃ¼r lokale Nutzung ohne Browser-Kontext).
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class Pyttsx3Engine:
    def __init__(self):
        self._engine = None
        self._q:     queue.Queue = queue.Queue()
        self._ready: bool        = False
        self._init()

    def _init(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   150)
            engine.setProperty("volume", 1.0)
            # Deutsche Stimme wÃ¤hlen
            for v in engine.getProperty("voices"):
                name = (v.name or "").lower()
                lang = str(v.languages or "").lower()
                if "de" in lang or "german" in name or "hedda" in name or "stefan" in name:
                    engine.setProperty("voice", v.id)
                    log.info(f"[pyttsx3] Deutsche Stimme: {v.name}")
                    break
            self._engine = engine
            self._ready  = True
            threading.Thread(target=self._worker, daemon=True, name="pyttsx3-worker").start()
            log.info("[pyttsx3] Engine bereit (Fallback-Modus).")
        except Exception as e:
            log.warning(f"[pyttsx3] Nicht verfÃ¼gbar: {e}")

    def _worker(self):
        """Serieller Worker â€” verhindert Engine-Konflikte."""
        while True:
            text = self._q.get()
            try:
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception as e:
                log.error(f"[pyttsx3] Worker-Fehler: {e}")
            finally:
                self._q.task_done()
            time.sleep(0.05)

    def say(self, text: str):
        if self._ready and text:
            self._q.put(text)

    def is_available(self) -> bool:
        return self._ready


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GLOBALE INSTANZEN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
edge_voice    = EdgeTTSEngine()
piper_voice   = PiperTTSEngine()
pyttsx3_voice = Pyttsx3Engine()

# RÃ¼ckwÃ¤rts-KompatibilitÃ¤t: jarvis_voice.say() fÃ¼r alte Aufrufe
class _LegacyVoice:
    """KompatibilitÃ¤ts-Wrapper. Neue Architektur: /api/tts â†’ Frontend spielt ab."""
    def say(self, text: str):
        if edge_voice.is_available():
            # Edge-TTS: im asyncio-Loop direkt spielen nicht sinnvoll ohne Audio-Output
            # Daher: Fallback auf pyttsx3 fÃ¼r direkte Backend-Ausgabe
            pyttsx3_voice.say(text)
        else:
            pyttsx3_voice.say(text)

jarvis_voice = _LegacyVoice()