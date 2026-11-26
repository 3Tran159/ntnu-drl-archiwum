from pathlib import Path
import time,subprocess,sys
root=Path(__file__).parent
deadline=time.time()+2400
while time.time()<deadline:
 if Path(r'E:\ntnu_cfd_night_20261028\probe_queue\queue_finished.json').exists():break
 time.sleep(10)
else:raise SystemExit('Probe did not finish; no additional task started')
subprocess.run([sys.executable,str(root/'run_star_task.py'),str(root/'B003/launch.json')],check=True)
