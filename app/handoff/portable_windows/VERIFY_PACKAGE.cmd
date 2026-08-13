@echo off
setlocal

set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Missing portable Python. Extract the complete ZIP first.
    pause
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
set "ARTIFACT_DIR=%APP_ROOT%\artifacts\lung_classifier\1.1.0"
set "HOST=127.0.0.1"
set "PORT=8000"
set "API_KEY_ENABLED=false"

cd /d "%APP_ROOT%"

echo [1/4] Checking portable Python...
"%PYTHON_EXE%" -c "import sys; print('Python', sys.version.split()[0]); print('Executable:', sys.executable)"
if errorlevel 1 goto :failed

echo.
echo [2/4] Checking model artifacts...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_artifacts.py"
if errorlevel 1 goto :failed

echo.
echo [3/4] Loading and warming up the real model...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_portable_runtime.py"
if errorlevel 1 goto :failed

echo.
echo [4/4] Checking FastAPI health routes...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\smoke_api.py"
if errorlevel 1 goto :failed

echo.
echo [PASS] Portable runtime, model, and API checks passed.
pause
exit /b 0

:failed
echo.
echo [FAIL] Package verification failed. See the message above.
pause
exit /b 1
