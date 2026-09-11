@echo off
setlocal EnableDelayedExpansion
title JARVIS - Piper TTS Installation
color 0B
echo.
echo  ================================================
echo   PIPER TTS - Lokale Stimme installieren
echo   Kein Internet noetig nach Installation!
echo  ================================================
echo.
cd /d "%~dp0"

:: Piper-Verzeichnis erstellen
if not exist "piper" mkdir piper
if not exist "piper\voices" mkdir piper\voices

:: Pruefen ob Piper schon da
if exist "piper\piper.exe" (
    echo  [OK] piper.exe bereits vorhanden.
    goto :check_voice
)

echo  [1/3] Lade piper.exe herunter...
echo  Quelle: github.com/rhasspy/piper
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_windows_amd64.zip' -OutFile 'piper\piper_win.zip'" 2>nul
if !errorlevel! neq 0 (
    echo  [FEHLER] Download fehlgeschlagen. Internet pruefen.
    pause
    exit /b 1
)

echo  [INFO] Entpacke piper.exe...
powershell -Command "Expand-Archive -Path 'piper\piper_win.zip' -DestinationPath 'piper' -Force" 2>nul
del /f /q piper\piper_win.zip 2>nul
echo  [OK] piper.exe installiert.

:check_voice
if exist "piper\voices\de_DE-thorsten-high.onnx" (
    echo  [OK] Deutsche Stimme bereits vorhanden.
    goto :done
)

echo.
echo  [2/3] Lade deutsche Stimme (Thorsten, ~60MB)...
powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx' -OutFile 'piper\voices\de_DE-thorsten-high.onnx'" 2>nul
powershell -Command "Invoke-WebRequest -Uri 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json' -OutFile 'piper\voices\de_DE-thorsten-high.onnx.json'" 2>nul

if exist "piper\voices\de_DE-thorsten-high.onnx" (
    echo  [OK] Stimme geladen.
) else (
    echo  [FEHLER] Stimme konnte nicht geladen werden.
    echo  Manuelle URL: huggingface.co/rhasspy/piper-voices
)

:done
echo.
echo  [3/3] Piper TTS bereit!
echo.
echo  In JARVIS Einstellungen: Stimme auf PIPER setzen.
echo  Volle Privatsphae - kein Internet mehr noetig!
echo.
pause
endlocal
