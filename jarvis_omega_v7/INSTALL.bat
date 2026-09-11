@echo off
setlocal EnableDelayedExpansion
title JARVIS OMNI v7.6 - INSTALLATION
color 0A

echo.
echo  ================================================
echo   JARVIS OMNI v7.6 - INSTALLATIONS-ASSISTENT
echo  ================================================
echo.
echo  Dieser Assistent richtet JARVIS auf deinem PC ein.
echo  Folge den Anweisungen auf dem Bildschirm.
echo.
pause

:: Verzeichnis setzen
cd /d "%~dp0"

:: PHASE 1: Python pruefen / installieren
echo.
echo  ================================================
echo   PHASE 1: Python pruefen
echo  ================================================

python --version >nul 2>nul
if %errorlevel% equ 0 goto :python_ok
python3 --version >nul 2>nul
if %errorlevel% equ 0 (set PYTHON=python3 & goto :python_ok)

echo.
echo  Python nicht gefunden!
echo.
echo  OPTION A: Automatisch installieren (winget)
echo  OPTION B: Manuell von python.org herunterladen
echo.
choice /C AB /N /M "  Waehle Option (A oder B): "
if !errorlevel! equ 1 goto :install_python_auto
goto :install_python_manual

:install_python_auto
echo  Installiere Python via winget...
winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if %errorlevel% equ 0 (
    echo  Python installiert. Starte neu falls noetig.
    set PYTHON=python
    goto :python_ok
)
echo  Winget fehlgeschlagen - bitte manuell installieren.

:install_python_manual
echo.
echo  Download-Seite wird geoeffnet...
start https://www.python.org/downloads/
echo  WICHTIG: Haken bei "Add Python to PATH" setzen!
echo  Nach der Installation diese Datei erneut starten.
pause
goto :end_error

:python_ok
set PYTHON=python
for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do set PY_VER=%%v
echo  [OK] %PY_VER%

:: PHASE 2: Pakete installieren
echo.
echo  ================================================
echo   PHASE 2: Python-Pakete installieren
echo  ================================================
echo  Kann einige Minuten dauern...
echo.

%PYTHON% -m pip install --upgrade pip --quiet
%PYTHON% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  [FEHLER] Paket-Installation fehlgeschlagen.
    echo  Bitte Internet-Verbindung pruefen.
    goto :end_error
)
echo  [OK] Alle Pakete installiert.

:: PHASE 3: Ollama pruefen
echo.
echo  ================================================
echo   PHASE 3: Ollama (KI-Engine)
echo  ================================================

where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Ollama gefunden.
    goto :ollama_ok
)

for %%d in (C D E F G H) do (
    if exist "%%d:\Ollama\ollama.exe" (
        echo  [OK] Ollama auf %%d:\
        goto :ollama_ok
    )
)

echo  Ollama nicht gefunden.
echo.
choice /C JN /N /M "  Ollama jetzt herunterladen? (J=Ja N=Nein): "
if !errorlevel! equ 1 (
    start https://ollama.ai
    echo.
    echo  Nach der Ollama-Installation:
    echo  1. Oeffne CMD und tippe: ollama pull qwen2.5:14b
    echo  2. Warte bis Download fertig
    echo  3. Starte dann JARVIS mit RUN_JARVIS.bat
)

:ollama_ok

:: PHASE 4: data-Ordner
echo.
echo  ================================================
echo   PHASE 4: Verzeichnisse erstellen
echo  ================================================
if not exist "data" mkdir data
if not exist "data\backups" mkdir data\backups
if not exist "docs" mkdir docs
echo  [OK] Verzeichnisse bereit.

:: PHASE 5: Desktop-Verknuepfung
echo.
echo  ================================================
echo   PHASE 5: Desktop-Verknuepfung
echo  ================================================
powershell -ExecutionPolicy Bypass -NonInteractive -File "%~dp0CREATE_SHORTCUT.ps1" >nul 2>nul
if %errorlevel% equ 0 (
    echo  [OK] Desktop-Verknuepfung erstellt.
) else (
    echo  [INFO] Verknuepfung manuell erstellen: Rechtsklick RUN_JARVIS.bat
)

:: FERTIG
echo.
echo  ================================================
echo   INSTALLATION ABGESCHLOSSEN
echo  ================================================
echo.
echo  JARVIS ist bereit!
echo.
echo  Starten: Doppelklick auf RUN_JARVIS.bat
echo           oder Desktop-Verknuepfung "JARVIS OMNI"
echo.
echo  Tipp: Sage "health" fuer einen System-Check.
echo.
choice /C JN /N /M "  JARVIS jetzt starten? (J=Ja N=Nein): "
if !errorlevel! equ 1 (
    start "" "%~dp0RUN_JARVIS.bat"
)
goto :end_ok

:end_error
echo.
echo  Installation konnte nicht abgeschlossen werden.
echo  Bitte Fehlermeldung oben lesen.

:end_ok
echo.
pause
endlocal
