"""Supervised mesh-selection queue. No wave runs until a mesh is selected."""
import ctypes,ctypes.wintypes as wt,json,os,re,sys,subprocess,time
from pathlib import Path
import run_until_settled as engine
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];K.OpenProcess.restype=wt.HANDLE
K.GetExitCodeProcess.argtypes=[wt.HANDLE,ctypes.POINTER(wt.DWORD)];K.CloseHandle.argtypes=[wt.HANDLE]
def running(pid):
 if not pid:return False
 h=K.OpenProcess(0x1000,False,int(pid))
 if not h:return False
 try:
  code=wt.DWORD()
  return bool(K.GetExitCodeProcess(h,ctypes.byref(code)) and code.value==259)
 finally:K.CloseHandle(h)
def read(p,d=None):return engine.read(p,d)
def jobs_ready():
 jobs=read(R/'mesh_selection_jobs.json',[])
 for j in jobs:
  if not re.fullmatch(r'M(0[2-9]|1[0-5])_until_settled_r[1-9][0-9]*',j['id']):raise RuntimeError('Unexpected mesh/attempt ID')
  mesh=j['id'].split('_')[0];met=read(Q/mesh/'measurement.json',{}).get('metrics',{});top=read(Q/mesh/'topology_audit.json',{})
  if met.get('cell_count')!=j['cells'] or not top.get('single_layer_topology'):raise RuntimeError(mesh+': mesh identity/topology check failed')
  if any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']):raise RuntimeError(mesh+': invalid cells')
  if not Path(j['source']).is_file():raise RuntimeError('Source absent: '+j['id'])
  if j.get('initialize') and j['start']!=0:raise RuntimeError('Nonzero restart cannot initialize')
 return jobs
def preflight():
 lock=read(R/'queue.lock',{})
 if running(lock.get('pid')):raise RuntimeError('An existing queue controller is active')
 for j in read(R/'queue.json',[]):
  p=read(R/j['id']/'process.json',{})
  if not (R/j['id']/'controller_result.json').exists() and running(p.get('launcher_pid')):raise RuntimeError('Existing solver still active: '+j['id'])
 pending=[]
 for j in jobs_ready():
  out=R/j['id'];done=read(out/'controller_result.json',{})
  if done.get('status')=='completed':continue
  if out.exists():raise RuntimeError('Unfinished attempt requires a separate restart ID: '+j['id'])
  pending.append(j)
 if engine.free_memory()<16*1024**3:raise RuntimeError('Less than 16 GiB free RAM')
 return pending
def main():
 pending=preflight()
 if '--run' not in sys.argv:
  print(json.dumps({'mode':'preflight_only','ready_cases':[j['id'] for j in pending],'would_start_solver':False}),flush=True);return
 lock=R/'queue.lock'
 if lock.exists():lock.rename(R/('queue_lock_recovered_'+time.strftime('%Y%m%d_%H%M%S')+'.json'))
 if (R/'STOP_ALL').exists():raise RuntimeError('STOP_ALL present; explicit pause recovery is required')
 with lock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'mesh selection, max M15, 1 percent CL/CD'},f)
 engine.write(R/'controller_process.json',{'pid':os.getpid(),'created_at':engine.stamp(),'mode':'mesh_selection'})
 K.SetThreadExecutionState(0x80000001);results=[]
 try:
  while True:
   if (R/'STOP_ALL').exists():break
   pending=[]
   for j in jobs_ready():
    result=read(R/j['id']/'controller_result.json',{})
    if result.get('status')=='completed':continue
    if (R/j['id']).exists():raise RuntimeError('Unfinished attempt needs review: '+j['id'])
    pending.append(j)
   if not pending:break
   job=pending[0];manifest=read(R/'queue.json',[])
   if not any(x['id']==job['id'] for x in manifest):manifest.append(job);engine.write(R/'queue.json',manifest)
   print('Starting '+job['id'],flush=True)
   result=engine.run_job(job);results.append(result);engine.write(R/'mesh_selection_results.json',results)
   print(job['id']+': '+result['status'],flush=True)
   post=subprocess.run([sys.executable,str(R/'refresh_settled.py')],capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
   if post.returncode:engine.write(R/'settled_post_error.json',{'case':job['id'],'error':post.stderr.decode(errors='replace')[-1600:]})
   if result['status']!='completed':break
  state='awaiting_mesh_selection' if all(r['status']=='completed' for r in results) and not (R/'STOP_ALL').exists() else 'needs_review'
  engine.write(R/'queue_state.json',{'status':state,'updated_at':engine.stamp(),'results':results,'waves_blocked_until_mesh_selected':True})
 except BaseException as e:
  engine.write(R/'queue_state.json',{'status':'controller_error','updated_at':engine.stamp(),'error':str(e),'results':results});raise
 finally:
  K.SetThreadExecutionState(0x80000000)
  if read(lock,{}).get('pid')==os.getpid():lock.unlink()
  engine.refresh()
if __name__=='__main__':main()
