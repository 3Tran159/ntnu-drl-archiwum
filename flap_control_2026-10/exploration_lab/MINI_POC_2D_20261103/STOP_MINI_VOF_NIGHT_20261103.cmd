@echo off
"C:\Users\ThinkPad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -c "from pathlib import Path; import json,time; p=Path(r'F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\mini_vof_20261103\NIGHT_20261103\STOP.json'); p.write_text(json.dumps(dict(reason='USER_STOP',at=time.time())))"
