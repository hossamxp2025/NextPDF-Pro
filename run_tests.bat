@echo off
rem NextPDF Pro - run the automated test suite
setlocal
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

set QT_QPA_PLATFORM=offscreen
set PYTHONIOENCODING=utf-8

%PY% -m pytest tests -v
set RESULT=%errorlevel%

echo.
if %RESULT% equ 0 (
    echo [OK] All tests passed.
) else (
    echo [FAIL] Tests reported failures.
)
if "%~1"=="" pause
exit /b %RESULT%
