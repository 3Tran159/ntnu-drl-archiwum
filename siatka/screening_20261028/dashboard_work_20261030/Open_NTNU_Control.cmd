@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Open_NTNU_Control.ps1"
if errorlevel 1 pause
