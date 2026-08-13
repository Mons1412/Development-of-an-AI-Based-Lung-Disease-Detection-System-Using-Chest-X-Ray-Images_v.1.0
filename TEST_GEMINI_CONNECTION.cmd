@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
cd /d "%APP_ROOT%"
"%PYTHON_EXE%" "%APP_ROOT%\scripts\test_gemini_connection.py"
pause
exit /b %ERRORLEVEL%
