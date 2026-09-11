@echo off
title JARVIS - EXE Builder
echo.
echo  ================================================
echo   JARVIS OMNI - EXE erstellen (K1)
echo  ================================================
echo.
cd /d "%~dp0"

echo  [1/3] Pruefe PyInstaller...
python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo  Installiere PyInstaller...
    python -m pip install pyinstaller --quiet
)
echo  [OK] PyInstaller bereit.

echo.
echo  [2/3] Baue JARVIS.exe...
echo  Kann 3-5 Minuten dauern.
python -m PyInstaller jarvis.spec --clean
if errorlevel 1 (
    echo  [FEHLER] Build fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo  [3/3] Fertig!
echo  EXE befindet sich in: dist\JARVIS_OMNI\JARVIS_OMNI.exe
echo.
pause
