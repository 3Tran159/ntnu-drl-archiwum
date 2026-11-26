"""Two-CPU zero-step no-foil preparation; never acquires or uses the GPU."""
import os,sys,json,time,subprocess,threading,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');case=W/'W20_H24_X4_Q2D_r2'
sys.path.insert(0,str(R));import run_until_settled as e
lock=W/'preparation.lock'
def state(status,**kw):e.write(R/'wave_preparation_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),workers=2,gpu=False,**kw))
def main():
 if lock.exists():raise RuntimeError('Another wave-preparation controller exists; inspect')
 with lock.open('x') as f:json.dump({'pid':os.getpid(),'case':case.name},f)
 try:
  if (R/'STOP_ALL').exists():state('paused_by_marker');return
  if (case/'build.log').exists():raise RuntimeError('Attempt already started; preserve and recover into a newID')
  if e.free_memory()<24*1024**3 or shutil.disk_usage(case).free<8*1024**3:raise RuntimeError('Insufficient headroom for CPU preparation')
  identity=e.read(case/'source_identity.json')
  if e.digest(Path(identity['source']))!=identity['source_sha256'] or e.digest(case/'baseline_copy.sim')!=identity['source_sha256']:raise RuntimeError('Source identity mismatch')
  env=dict(os.environ,NTNU_WAVE_JOB=str(case/'job.json'))
  started=time.time();state('building_24m_nofoil_on_CPU',scope='Mesh and zero-step initialization/profile audit; no transient validation')
  with (case/'build.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(2),'-batch',str(case/'WaveTankBuild24m.java'),str(case/'baseline_copy.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(case/'process.json',{'launcher_pid':p.pid,'started_at':e.stamp(),'start_unix':started,'workers':2,'gpu':False})
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   t=threading.Thread(target=drain,daemon=True);t.start()
   while p.poll() is None:
    if time.time()-started>1800 or e.free_memory()<12*1024**3 or (R/'STOP_ALL').exists():
     subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError('Owned CPU preparation stopped due timeout/resources/user marker; attempt preserved')
    state('building_24m_nofoil_on_CPU',elapsed_s=time.time()-started,free_GiB=e.free_memory()/1024**3,launcher_pid=p.pid)
    time.sleep(15)
   rc=p.wait();t.join(10)
  audit=e.read(case/'initial_audit.json',{})
  preserved=e.digest(Path(identity['source']))==identity['source_sha256'] and e.digest(case/'baseline_copy.sim')==identity['source_sha256']
  result={'returncode':rc,'elapsed_wall_s':time.time()-started,'source_unchanged':preserved,'audit':audit,'built_sim_exists':(case/'built.sim').exists()}
  e.write(case/'build_result.json',result)
  if rc or not preserved or not (case/'SUCCESS.txt').exists() or not (case/'built.sim').exists() or audit.get('steps_taken')!=0:raise RuntimeError('CPU build/audit did not complete')
  if audit.get('first_wave_front') is not False or audit.get('depth_m')!=24 or abs(audit.get('span_m',0)-.02)>1e-9:raise RuntimeError('Wave scope audit mismatch')
  state('built_pending_topology_and_transient_checks',result=result,scope='Zero-step only; no propagation or wave-force validation')
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
