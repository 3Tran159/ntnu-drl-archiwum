@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dashboard.ps1"
if errorlevel 1 (
  echo Startup failed. See server.log in this folder.
  pause
)
