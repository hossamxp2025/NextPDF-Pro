@echo off
rem NextPDF Pro - UI and acceptance tests (headless)
setlocal
cd /d "%~dp0.."

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
set QT_QPA_PLATFORM=offscreen
set PYTHONIOENCODING=utf-8

%PY% -m pytest tests\test_modern_ui.py tests\test_regression_ui.py tests\test_acceptance.py -v
set RESULT=%errorlevel%
echo.
if %RESULT% equ 0 (echo [OK] UI tests passed.) else (echo [FAIL] UI tests failed.)
exit /b %RESULT%
