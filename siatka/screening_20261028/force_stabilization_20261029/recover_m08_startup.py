"""Recover M08 startup without changing any guard or source attempt."""
import os,sys,json,subprocess,ctypes,csv,math
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent
def publish(j):
 a=e.read(R/'queue.json',[])
 if any(x['id']==j['id'] for x in a):raise RuntimeError('Attempt already recorded')
 a.append(j);e.write(R/'queue.json',a)
def main():
 lock=R/'queue.lock'
 if lock.exists():raise RuntimeError('Campaign lock exists; inspect owner')
 if (R/'STOP_ALL').exists():raise RuntimeError('Campaign is paused')
 for j in e.read(R/'queue.json',[]):
  if not (R/j['id']/'controller_result.json').exists() and running(e.read(R/j['id']/'process.json',{}).get('launcher_pid')):raise RuntimeError('Solver still active')
 with lock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M08 guarded startup recovery'},f)
 e.write(R/'controller_process.json',{'pid':os.getpid(),'mode':'M08_recovery','created_at':e.stamp()})
 ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
 try:
  warm={'id':'M08_startup_r2','source':str(R/'M08_until_settled_r1/restart_prepared.sim'),'start':0,'initialize':False,'cells':254989,'dt':.0005,'inner':50,'order':'FIRST_ORDER','target':.020,'wall_budget_s':1800,'purpose':'Reduced-step startup, no guard relaxation; not an accepted force result'}
  publish(warm);result=e.run_job(warm)
  e.write(R/'M08_recovery_state.json',{'stage':'startup_complete','result':result})
  if not(result['returncode']==0 and result['completed'].get('status')=='target_reached' and result['original_unchanged']):raise RuntimeError('M08 reduced-step startup did not pass; inspect preserved attempt')
  with (R/warm['id']/'history.csv').open() as f:rows=[{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
  if len(rows)!=40 or any(not all(math.isfinite(v) for v in a.values()) for a in rows) or rows[-1]['max_velocity_m_s']>50:raise RuntimeError('Warmup end-state validation failed')
  e.write(R/warm['id']/'startup_acceptance.json',{'status':'startup_checkpoint_only','time_s':rows[-1]['physical_time_s'],'last_max_velocity_m_s':rows[-1]['max_velocity_m_s'],'not_force_accepted':True})
  job={'id':'M08_until_settled_r3','source':str(R/warm['id']/'final.sim'),'start':rows[-1]['physical_time_s'],'initialize':False,'cells':254989,'dt':.001,'inner':20,'order':'FIRST_ORDER','target':10,'wall_budget_s':10800,'prior_history':str(R/warm['id']/'history.csv'),'termination':'First passing adjacent 0.2 s means below0.5%'}
  jobs=e.read(R/'mesh_selection_jobs.json',[])
  backup=R/'mesh_selection_jobs_before_M08_recovery.json'
  if not backup.exists():e.write(backup,jobs)
  jobs=[x for x in jobs if not x['id'].startswith('M08_')]+[job];e.write(R/'mesh_selection_jobs.json',jobs)
  publish(job);result=e.run_job(job)
  e.write(R/'M08_recovery_state.json',{'stage':'flow_complete','result':result})
  p=subprocess.run([sys.executable,str(R/'refresh_settled.py')],capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  if p.returncode:e.write(R/'settled_post_error.json',{'case':job['id'],'error':p.stderr.decode(errors='replace')[-1600:]})
  e.write(R/'queue_state.json',{'status':'awaiting_mesh_selection' if result['status']=='completed' else 'needs_review','updated_at':e.stamp(),'results':[result],'waves_blocked_until_mesh_selected':True})
 except BaseException as ex:
  e.write(R/'M08_recovery_state.json',{'stage':'needs_review','error':str(ex)})
  e.write(R/'queue_state.json',{'status':'needs_review','updated_at':e.stamp(),'error':str(ex),'waves_blocked_until_mesh_selected':True})
  raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  e.refresh()
if __name__=='__main__':main()
