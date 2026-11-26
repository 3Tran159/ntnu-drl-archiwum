@echo off
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 "F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\recovered_sweep_control.py" --check
if errorlevel 1 exit /b 2
powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -ArgumentList '-X','utf8','-u','F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\recovered_sweep_control.py','start'"
