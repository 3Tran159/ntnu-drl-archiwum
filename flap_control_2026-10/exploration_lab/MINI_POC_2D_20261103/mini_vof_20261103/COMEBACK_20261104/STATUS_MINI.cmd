@echo off
setlocal
if exist "%~dp0DAY_QUEUE.json" type "%~dp0DAY_QUEUE.json"
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 "%~dp0run_day.py" status
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 "%~dp0run_night.py" status
