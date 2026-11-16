@echo off
rem NextPDF Pro - syntax/compile check for all Python sources
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

%PY% -m compileall -q src tests
if errorlevel 1 (
    echo [FAIL] Compilation errors found.
    exit /b 1
)
echo [OK] All Python files compile.
endlocal
