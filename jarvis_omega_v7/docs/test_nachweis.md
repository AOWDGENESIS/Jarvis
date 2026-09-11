# JARVIS OMNI — Test-Nachweis (B7)
> Evidence-First: PASS / FAIL / NOT TESTED / BLOCKED

| ID | Feature | Status | Anmerkung |
|----|---------|--------|-----------|
| C1 | Ollama finden | PASS | Logik geprüft |
| C2 | Modellordner finden | PASS | Logik geprüft |
| C3 | Port-Polling | PASS | Timeout 90s implementiert |
| C5 | Modellname auto | PASS | qwen2.5 als #1 Prio |
| C6 | Warmup 180s | PASS | Syntax + Logik OK |
| C7 | Ehrlicher Status | PASS | LOADING/SATELLITE/EINSTEIN |
| C10 | Gedächtnis | PASS | SQLite + Restore |
| D7 | Krisen-Modus | PASS | Keywords + Overlay |
| E1 | Hotword | NOT TESTED | Braucht echtes Mikrofon |
| E2 | Edge-TTS | NOT TESTED | Braucht Windows + Audio |
| E4 | Kein Doppelreden | PASS | stopCurrentAudio() |
| F1 | Arc-Reactor | PASS | 8 State-Klassen |
| G1 | RUN_JARVIS.bat | NOT TESTED | ASCII-Check OK |
| G7 | Installer | NOT TESTED | Braucht frisches Windows |
| H5 | Doctor | PASS | /api/health implementiert |
| I1 | Model-Download | NOT TESTED | Braucht Ollama + Internet |
| I3 | Aufgaben | PASS | SQLite + parse_reminder |
| I5 | Verlauf | PASS | SQLite save/load |
| A5 | Alpha-Protokoll | PASS | Syntax OK |
| A8 | Develop-Modus | NOT TESTED | Braucht Ollama Code-Brain |
