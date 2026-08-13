@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_ROOT%\scripts\SET_GEMINI_KEY.ps1" -ProjectRoot "%APP_ROOT%"
if errorlevel 1 (
  echo [ERROR] Gemini key setup failed.
  pause
  exit /b 1
)
echo.
echo Run TEST_GEMINI_CONNECTION.cmd to verify the online provider.
pause
