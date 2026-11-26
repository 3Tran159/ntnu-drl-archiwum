@echo off
if /I "%~1"=="START" goto start
if /I "%~1"=="STOP" goto stop
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "C:\Users\ThinkPad\Documents\ChatGPT\ntnu science\flap_storage\manager.py" --status
exit /b
:start
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -c "import sys;sys.path.insert(0,'C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_storage');import manager;manager.ensure_running(explicit=True)"
exit /b
:stop
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "C:\Users\ThinkPad\Documents\ChatGPT\ntnu science\flap_storage\manager.py" --stop
