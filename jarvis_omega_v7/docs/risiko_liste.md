# JARVIS OMNI — Risiko-Liste / Threat Model (B5)

## Risiko-Bewertung: HOCH / MITTEL / NIEDRIG

### HOCH

| ID | Risiko | Massnahme |
|----|--------|-----------|
| R1 | Ollama ladet falsches Modell | _pick_best_model() mit Prioritaetsliste |
| R2 | Port 8000 von fremdem Prozess belegt | Gezielter taskkill via psutil (A7-konform) |
| R3 | Edge-TTS sendet Daten an Microsoft | Opt-in in Einstellungen, Fallback pyttsx3 |
| R4 | bat-Datei crasht bei Sonderzeichen | Reines ASCII (CP1252), kein Unicode |
| R5 | Jarvis beendet fremde Prozesse | Alpha-Protokoll blockiert gefaehrliche Cmds |

### MITTEL

| ID | Risiko | Massnahme |
|----|--------|-----------|
| R6 | Ollama nicht installiert | G3 Dialog + Download-Link |
| R7 | Python nicht im PATH | bat prueft python + python3 |
| R8 | pyaudio baut nicht | Optional, Browser-Mikrofon als Fallback |
| R9 | SQLite-Datei beschaedigt | WAL-Modus, Mutex, separate Backup-Tabelle |
| R10| Develop-Modus ueberschreibt Datei | Automatisches Backup vor jeder Aenderung |
| R11| Krisen-Erkennung zu empfindlich | Keyword-Liste bewusst konservativ |

### NIEDRIG

| ID | Risiko | Massnahme |
|----|--------|-----------|
| R12| Browser oeffnet sich nicht | webbrowser.open() mit Port-Wartecheck |
| R13| Gesprächsverlauf zu lang | MAX_HISTORY = 10 Austausche |
| R14| Reminder feuert mehrfach | notified=1 nach erstem Trigger |
| R15| Desktop-Shortcut schlaegt fehl | CREATE_SHORTCUT.ps1 mit Fehlerbehandlung |

## Akzeptierte Kompromisse

| Thema | Kompromiss | Begruendung |
|-------|------------|-------------|
| A4 Lokal-First | Edge-TTS -> Microsoft | Qualitaet >> Privatsphäre (opt-in) |
| PyAudio | Nicht installierbar ohne Build-Tools | Browser-Mikrofon ausreichend |
| Ollama Modellgroesse | qwen2.5:14b passt, 70B nicht | RTX 3060 12GB VRAM Limit |
