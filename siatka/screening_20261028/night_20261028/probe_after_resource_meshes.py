from pathlib import Path
import time,subprocess,sys,json
root=Path(__file__).parent
end=time.time()+1800
while time.time()<end:
 if (root/'resource_mesh_queue_finished.json').exists():break
 time.sleep(10)
else:raise SystemExit('Resource meshes exceeded waiting budget')
if not (root/'D001/measurement.json').exists():raise SystemExit('Missing D001 mesh evidence')
subprocess.run([sys.executable,str(root/'night_queue.py'),str(root/'probe_D001_manifest.json')],check=True)
