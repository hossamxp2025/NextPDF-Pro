@echo off
rem NextPDF Pro - full verification: compile check + complete test suite
setlocal
cd /d "%~dp0.."

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set QT_QPA_PLATFORM=offscreen
set PYTHONIOENCODING=utf-8

echo [1/2] Compile check...
%PY% -m compileall -q src tests
if errorlevel 1 (
    echo [FAIL] Compilation errors found.
    exit /b 1
)

echo [2/2] Test suite...
%PY% -m pytest tests -v
set RESULT=%errorlevel%
echo.
if %RESULT% equ 0 (
    echo [OK] Verification complete: all tests passed.
) else (
    echo [FAIL] Verification failed.
)
if "%~1"=="" pause
exit /b %RESULT%
