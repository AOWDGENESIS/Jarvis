@echo off
title JARVIS DIAGNOSE
color 0E

echo.
echo  ================================================
echo   JARVIS DIAGNOSE - zeigt genau was fehlt
echo  ================================================
echo.

cd /d "%~dp0"
echo  Verzeichnis: %CD%
echo.

echo  [1] Python:
python --version 2>nul
if %errorlevel% neq 0 (
    echo  XX Python NICHT gefunden!
    echo     Installieren: https://www.python.org/downloads/
) else (
    echo  OK Python gefunden.
)
echo.

echo  [2] Wichtige Pakete:
python -c "import fastapi" 2>nul && echo  OK fastapi || echo  XX fastapi fehlt
python -c "import uvicorn" 2>nul && echo  OK uvicorn || echo  XX uvicorn fehlt
python -c "import psutil"  2>nul && echo  OK psutil  || echo  XX psutil fehlt
python -c "import requests"2>nul && echo  OK requests|| echo  XX requests fehlt
python -c "import edge_tts"2>nul && echo  OK edge_tts|| echo  XX edge_tts fehlt - TTS eingeschraenkt
python -c "import pyttsx3" 2>nul && echo  OK pyttsx3 || echo  XX pyttsx3 fehlt
echo.

echo  [3] Ollama:
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo  OK Ollama in PATH
    echo  Installierte Modelle:
    ollama list
) else (
    echo  XX Ollama nicht in PATH
    for %%d in (C D E F G H) do (
        if exist "%%d:\Ollama\ollama.exe" (
            echo  OK Ollama auf %%d:\Ollama\ollama.exe
        )
    )
)
echo.

echo  [4] Port 8000:
netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING"
if %errorlevel% equ 0 (
    echo  INFO Port 8000 ist belegt - wird beim Start freigegeben.
) else (
    echo  OK Port 8000 frei.
)
echo.

echo  [5] Dateien:
if exist "main.py"               echo  OK main.py
if not exist "main.py"           echo  XX main.py FEHLT!
if exist "core\brain.py"         echo  OK core\brain.py
if not exist "core\brain.py"     echo  XX core\brain.py FEHLT!
if exist "core\scanner.py"       echo  OK core\scanner.py
if exist "core\db.py"            echo  OK core\db.py
if not exist "core\db.py"        echo  XX core\db.py FEHLT!
if exist "frontend\index.html"   echo  OK frontend\index.html
if exist "requirements.txt"      echo  OK requirements.txt
echo.

echo  ================================================
echo   Druecke eine Taste zum Schliessen.
echo  ================================================
pause >nul
