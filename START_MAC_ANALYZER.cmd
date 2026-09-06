@echo off
setlocal
cd /d "%~dp0"
title MAC Analyzer Pro Launcher

if exist "%~dp0.venv-portable\Scripts\python.exe" (
  "%~dp0.venv-portable\Scripts\python.exe" "%~dp0scripts\portable_launcher.py" --root "%~dp0." %*
  if not errorlevel 1 goto launcher_success
)
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\portable_launcher.py" --root "%~dp0." %*
  if not errorlevel 1 goto launcher_success
)
if exist "%~dp0runtime\python\python.exe" (
  "%~dp0runtime\python\python.exe" "%~dp0scripts\portable_launcher.py" --root "%~dp0." %*
  if not errorlevel 1 goto launcher_success
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0scripts\portable_launcher.py" --root "%~dp0." %*
  if not errorlevel 1 goto launcher_success
)
where python >nul 2>nul
if not errorlevel 1 (
  python "%~dp0scripts\portable_launcher.py" --root "%~dp0." %*
  if not errorlevel 1 goto launcher_success
)

rem Compatibility fallback for a computer without Python.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable_start.ps1" %*

:launcher_result
if errorlevel 1 (
  echo.
  echo MAC Analyzer Pro could not be started. See the message above.
  pause
  exit /b 1
)
:launcher_success
exit /b 0
