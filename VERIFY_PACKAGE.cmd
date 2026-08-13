@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
set "ARTIFACT_DIR=%APP_ROOT%\artifacts\lung_classifier\1.1.0"
set "ONLINE_AI_ENABLED=false"
cd /d "%APP_ROOT%"

echo [1/5] Portable Python and required imports...
"%PYTHON_EXE%" -c "import google.genai, reportlab, tensorflow; print('runtime_imports=PASS')"
if errorlevel 1 goto :failed
echo [2/5] Model artifact checksums...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_artifacts.py"
if errorlevel 1 goto :failed
echo [3/5] Model load and warm-up...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_portable_runtime.py"
if errorlevel 1 goto :failed
echo [4/5] FastAPI health routes...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\smoke_api.py"
if errorlevel 1 goto :failed
echo [5/5] Offline test suite...
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :failed
echo [PASS] Portable package verification passed.
pause
exit /b 0

:failed
echo [FAIL] Package verification failed.
pause
exit /b 1
