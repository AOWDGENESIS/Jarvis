# JARVIS OMNI — Applicability Matrix (B6)

> Welche Funktion auf welchem System verfuegbar ist.

## Legende
- OK = Verfuegbar und getestet
- OPT = Optional / bedingt verfuegbar  
- NO = Nicht verfuegbar
- NT = Noch nicht getestet

## Hardware-Matrix

| Feature | RTX 3060 12GB | RTX 3060 6GB | CPU-only | Raspberry Pi |
|---------|:---:|:---:|:---:|:---:|
| qwen2.5:14b | OK | OPT | OPT | NO |
| deepseek-coder-v2 | OK | OPT | OPT | NO |
| llama3:8b | OK | OK | OK | OPT |
| llama3.2:3b | OK | OK | OK | OK |
| Edge-TTS | OK | OK | OK | OK |
| Hotword | OK | OK | OK | OPT |
| Live-Graph | OK | OK | OK | NO |

## OS-Matrix

| Feature | Windows 11 | Windows 10 | Linux | macOS |
|---------|:---:|:---:|:---:|:---:|
| RUN_JARVIS.bat | NT | NT | NO | NO |
| Python-Stack | OK | OK | OK | OK |
| Ollama | OK | OK | OK | OK |
| Edge-TTS | OK | OK | OK | OK |
| Desktop-Shortcut | NT | NT | NO | NO |
| Hotword WebSpeech | OK | OPT | OPT | OK |

## Feature-Status fuer Felix's System

| Kategorie | Feature | Status |
|-----------|---------|--------|
| KI-Kern | qwen2.5:14b | OK |
| KI-Kern | deepseek-coder-v2 | OK |
| Sprache | Edge-TTS KatjaNeural | NT |
| Sprache | Hotword | NT |
| UI | Arc-Reactor | OK |
| UI | Weltkarte | OK |
| Daten | SQLite Aufgaben | OK |
| Daten | Gesprächsverlauf | OK |
| Start | RUN_JARVIS.bat | NT |
| Start | INSTALL.bat | NT |
