@echo off
rem NextPDF Pro - run from source
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

%PY% -c "import PySide6, pymupdf" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Missing dependencies. Installing requirements...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Could not install dependencies.
        pause
        exit /b 1
    )
)

%PY% -m src.main
if errorlevel 1 (
    echo.
    echo [ERROR] NextPDF Pro exited with an error.
    pause
    exit /b 1
)
endlocal
