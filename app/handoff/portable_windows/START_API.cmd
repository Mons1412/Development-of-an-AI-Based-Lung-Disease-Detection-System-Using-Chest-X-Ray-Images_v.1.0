@echo off
setlocal

set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Missing portable Python: "%PYTHON_EXE%"
    echo Extract the complete ZIP before running this file.
    pause
    exit /b 1
)

if not exist "%APP_ROOT%\artifacts\lung_classifier\1.1.0\lung_classifier_v1.keras" (
    echo [ERROR] Missing model artifact.
    echo Extract the complete ZIP before running this file.
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

if not "%~1"=="" set "PORT=%~1"

cd /d "%APP_ROOT%"

echo [1/2] Verifying model files...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_artifacts.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Model verification failed. See the message above.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting Lung X-ray FastAPI...
echo Demo UI : http://127.0.0.1:%PORT%/demo
echo API docs: http://127.0.0.1:%PORT%/docs
echo Stop     : Press Ctrl+C
echo.

"%PYTHON_EXE%" -m lung_xray_api
set "APP_EXIT_CODE=%ERRORLEVEL%"

if not "%APP_EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] The API stopped with exit code %APP_EXIT_CODE%.
    pause
)

exit /b %APP_EXIT_CODE%
