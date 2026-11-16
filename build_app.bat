@echo off
rem NextPDF Pro - build the standalone EXE
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

%PY% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed for %PY%.
    echo         Install it with: %PY% -m pip install pyinstaller
    pause
    exit /b 1
)

%PY% build\build_exe.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Build output: dist\release-1.1.0\NextPDF-Pro.exe
if "%~1"=="" pause
endlocal
