@echo off
rem NextPDF Pro - build the Inno Setup installer from dist\release-1.1.0
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if not exist "dist\release-1.1.0\NextPDF-Pro.exe" (
    echo [ERROR] Build the EXE first: build_app.bat
    pause
    exit /b 1
)

%PY% build\build_exe.py --installer
if errorlevel 1 (
    echo [ERROR] Installer build failed.
    echo         Inno Setup 6 is required: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

echo.
echo Installer output: dist\release-1.1.0\NextPDF-Pro-Setup-1.1.0.exe
if "%~1"=="" pause
endlocal
