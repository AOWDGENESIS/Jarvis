@echo off
title JARVIS OMNI
color 0B
cd /d "%~dp0"
echo.
echo  ================================================
echo   JARVIS OMNI - START
echo   Verzeichnis: %CD%
echo  ================================================
echo.
echo  Starte Jarvis (Browser oeffnet sich gleich)...
echo  Dieses Fenster OFFEN lassen!
echo.
set "PYCMD=py"
where py >nul 2>nul
if errorlevel 1 set "PYCMD=python"
echo  Verwende Python-Befehl: %PYCMD%
echo.
%PYCMD% main.py
echo.
echo  ================================================
echo   Jarvis ist beendet (oder oben steht ein Fehler).
echo   Fenster bleibt offen - Druecke eine Taste.
echo  ================================================
echo.
pause
