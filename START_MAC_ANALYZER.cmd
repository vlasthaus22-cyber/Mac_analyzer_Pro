@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable_start.ps1"
if errorlevel 1 (
  echo.
  echo MAC Analyzer Pro could not be started. See the message above.
  pause
)
