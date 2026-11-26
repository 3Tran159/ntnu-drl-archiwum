@echo off
powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -ArgumentList '-X','utf8','-u','F:\ntnu\flap_control\hydro_validation_2606_20261102\tools\cfd_control.py','start'"
