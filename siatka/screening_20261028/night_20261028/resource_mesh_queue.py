from pathlib import Path
import subprocess,sys,json,concurrent.futures,time
from night_queue import free_memory,GIB
root=Path(__file__).parent

def run(case):
 while free_memory()<20*GIB:
  if (root/'STOP_RESOURCE').exists():return {'case':case,'status':'stopped_before_launch'}
  time.sleep(10)
 if (root/'STOP_RESOURCE').exists():return {'case':case,'status':'stopped_before_launch'}
 p=subprocess.run([sys.executable,str(root/'run_star_task.py'),str(root/case/'launch.json')])
 result={'case':case,'returncode':p.returncode,'measurement_exists':(root/case/'measurement.json').exists()}
 (root/case/'queue_result.json').write_text(json.dumps(result));return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(run,['D001','D002','D003','D004']))
(root/'resource_mesh_queue_finished.json').write_text(json.dumps(results,indent=2))
print('Resource mesh queue finished',results)
