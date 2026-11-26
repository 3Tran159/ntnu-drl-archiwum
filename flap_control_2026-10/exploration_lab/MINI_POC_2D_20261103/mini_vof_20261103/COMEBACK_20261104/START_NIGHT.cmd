@echo off
setlocal
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 "%~dp0run_night.py" start
exit /b %ERRORLEVEL%
