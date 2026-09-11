# JARVIS OMNI — Technische Spezifikation v7.6

## Architektur
```
RUN_JARVIS.bat
    └── python main.py (FastAPI, Port 8000)
         ├── core/scanner.py   — Ollama-Finder + Dual-Brain-Routing
         ├── core/brain.py     — EinsteinCore (qwen2.5:14b + deepseek-coder-v2)
         ├── core/voice.py     — Edge-TTS + pyttsx3 Fallback
         ├── core/db.py        — SQLite (Aufgaben + Verlauf)
         ├── core/alpha.py     — Sicherheitslayer
         ├── core/develop.py   — Develop-Modus
         └── frontend/index.html — Fusion UI (Vanilla HTML/CSS/JS)
```

## API-Endpunkte
| Endpoint | Methode | Funktion |
|----------|---------|---------|
| /api/status | GET | Aktueller Modus, CPU, RAM, Modell |
| /api/command | POST | Befehl senden, Antwort erhalten |
| /api/tts | POST | Text → MP3 (Edge-TTS) |
| /api/voices | GET | Verfügbare Stimmen |
| /api/tasks | GET/POST | Aufgaben lesen/erstellen |
| /api/tasks/{id}/done | PATCH | Aufgabe erledigt |
| /api/tasks/{id} | DELETE | Aufgabe löschen |
| /api/reminders/check | GET | Fällige Erinnerungen |
| /api/history | DELETE | Verlauf löschen |
| /api/history/load | GET | Verlauf laden |
| /api/health | GET | System-Diagnose |
| /api/models/pull | POST | Modell herunterladen |
| /api/models/pull/status | GET | Download-Fortschritt |
| /api/models/list | GET | Installierte Modelle |
| /api/develop/propose | POST | Code-Vorschlag erstellen |
| /api/develop/confirm | POST | Code-Vorschlag bestätigen |
| /api/develop/reject | POST | Code-Vorschlag ablehnen |
| /api/develop/status | GET | Develop-Status |
| /api/devices | GET | Verbundene Geräte (I7) |
| /api/privacy | GET/POST | Privatsphäre-Einstellungen (I6) |

## Datenbank (SQLite)
- `data/jarvis.db` — Aufgaben + Gesprächsverlauf
- `data/security.log` — Alpha-Protokoll Audit-Trail
- `data/privacy.json` — Privatsphäre-Einstellungen
- `data/backups/` — Develop-Modus Backups

## Hardware-Anforderungen (Felix's System)
- Windows 11 Pro
- RTX 3060 12GB VRAM
- 24GB RAM
- Ryzen 5 5600G
- Ollama mit qwen2.5:14b + deepseek-coder-v2
