# JARVIS OMNI v7.6 OMEGA — FORTSCHRITT.md
> Session-Failover · Master-Prompt v8.0 · Bei Token-Reset: Datei laden → NÄCHSTER SCHRITT

---

## AKTUELLER STAND

**Datum:** 26.08.2026 · **Phase:** 7 — Voice Engine · **RUN:** 4

---

## FERTIG (Evidence: PASS / NOT TESTED auf echtem Windows)

| ID | Beschreibung | Datei | Status |
|----|-------------|-------|--------|
| C1–C9 | Ollama: Auto-Find, Model-Select, Warmup, Status | scanner.py + brain.py | PASS |
| C10 | Gesprächsgedächtnis (10 Austausche, thread-safe) | brain.py | PASS |
| D4–D6 | Keine fremden Prozesse, Port gezielt, kein taskkill | scanner.py + main.py | PASS |
| E2 | Klare Stimme: Edge-TTS KatjaNeural (Neural) | voice.py + /api/tts | PASS (NOT TESTED Windows) |
| E3 | Satz-für-Satz TTS (splitSentences) | index.html | PASS |
| E4 | Kein Doppelreden: stopCurrentAudio() überall | index.html + main.py | PASS |
| E5 | Stimme schaltbar: EDGE / BROWSER / AUS | index.html + /api/voices | PASS |
| E6 | Edge-TTS primär, pyttsx3 Fallback | voice.py | PASS (NOT TESTED Windows) |
| F1–F9 | Fusion UI: Arc-Reactor, Panels, Telemetrie | index.html | PASS |
| G1 | Sicheres Start-Skript | RUN_JARVIS.bat | NOT TESTED Windows |
| G8 | Browser öffnet automatisch | main.py | NOT TESTED Windows |
| H4 | Kein dauerhafter Satellite-Modus | brain.py + scanner.py | PASS |
| A1 | Doppelklick-Starter | RUN_JARVIS.bat | NOT TESTED Windows |

---

## NEUE ENDPUNKTE (diese Session)

| Endpoint | Methode | Funktion |
|----------|---------|----------|
| /api/tts | POST | Text → MP3 (Edge-TTS), E2/E4/E6 |
| /api/voices | GET | Alle deutschen Stimmen + edge_tts_ok |
| /api/history | DELETE | Gesprächsverlauf löschen (C10) |

---

## NÄCHSTE PRIORITÄTEN

| ID | Beschreibung | Aufwand |
|----|-------------|---------|
| H1 | Echte Zustände: BOOTING/LISTENING/SPEAKING/ERROR im Arc | Klein |
| H5 | Doctor-Befehl: `jarvis health` → prüft alles durch | Mittel |
| G3 | Fehlende Teile erkennen & fragen (Ollama fehlt → Dialog) | Mittel |
| G5/G6 | Desktop-Verknüpfung + eigenes Icon | Klein |
| I3 | Aufgaben & Erinnerungen | Mittel |
| I5 | Gesprächsprotokoll in SQLite speichern | Mittel |
| G7 | Installer (.exe) | Groß |

---

## DATEI-INVENTAR (v7.6.4)

```
jarvis_omega_v7/
├── main.py                  ← v4 (tts/voices/history Endpunkte, E4-fix)
├── requirements.txt         ← v3 (+ edge-tts>=6.1.12)
├── RUN_JARVIS.bat           ← v1 (Doppelklick-Starter)
├── FORTSCHRITT.md           ← v2 (dieser Tracker)
├── core/
│   ├── scanner.py           ← v2 (Poll-Wait, Model-Discovery)
│   ├── brain.py             ← v3 (Warmup, History C10)
│   └── voice.py             ← v2 (EdgeTTS + pyttsx3 Fallback)
└── frontend/
    └── index.html           ← v4 (speakEdge, stopCurrentAudio, /api/voices)
```

---

## BEKANNTE EINSCHRÄNKUNGEN (NOT TESTED)

- `edge-tts` braucht Internet → Microsoft-Server (A4 Kompromiss, opt-in via Settings)
- `pyaudio` kann auf Windows ohne Build-Tools fehlschlagen → bat zeigt Hinweis
- Whisper-STT noch nicht integriert (Browser-WebSpeech Übergangslösung)
- Windows-Tests fehlen komplett — bitte nach Einbau sofort melden was nicht klappt
