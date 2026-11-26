from pathlib import Path
import time,subprocess,sys
root=Path(__file__).parent
deadline=time.time()+1800
while time.time()<deadline:
 if all((root/c/'star_exit.json').exists() for c in ['B001','B002']):break
 time.sleep(10)
else:raise SystemExit('Mesh tasks did not finish within probe wait budget')
subprocess.run([sys.executable,str(root/'night_queue.py'),str(root/'probe_manifest.json')],check=True)
