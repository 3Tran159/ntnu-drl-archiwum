"""Wait for the existing CPU pilot to release its lock, then export its saved fields without advancing time."""
import os,sys,time,json,shutil,subprocess,threading
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');C=W/'W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3';A=W/'W20_H24_X4_GPUprop_r3_backflow_audit_r1'
import run_until_settled as e
from mesh_selection_queue import running
own=R/'wave_backflow_audit.lock';cpu=W/'preparation.lock'
def state(status,**kw):e.write(R/'wave_backflow_audit_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=C.name,directory=str(A),**kw))
def main():
 if own.exists():raise RuntimeError('Audit controller exists; inspect before recovery')
 with own.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Wait for CPU pilot then zero-step saved-field audit'),f)
 claimed=False
 try:
  state('waiting_for_CPU_pilot')
  while cpu.exists() or running(28480):
   if (R/'STOP_ALL').exists():state('paused_by_marker');return
   time.sleep(15)
  if (R/'STOP_ALL').exists():state('paused_by_marker');return
  if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Insufficient audit resources')
  if A.exists():raise RuntimeError('Audit attempt exists; preserve and use a new ID')
  source=C/'final.sim'
  if not source.exists():
   points=sorted(C.glob('checkpoint_t*.sim'),key=lambda p:p.stat().st_mtime)
   if not points:raise RuntimeError('Pilot has no saved transient checkpoint')
   source=points[-1]
  with cpu.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Zero-step saved-wave-field export',case=A.name),f)
  claimed=True;A.mkdir();shutil.copy2(source,A/'input.sim');shutil.copy2(R/'AuditWaveBackflow.java',A/'AuditWaveBackflow.java')
  digest=e.digest(source)
  if e.digest(A/'input.sim')!=digest:raise RuntimeError('Audit copy hash mismatch')
  e.write(A/'source_identity.json',dict(source=str(source),source_sha256=digest,copy_sha256=digest,pilot_completed=e.read(C/'completed.json',{}),scope='Zero-step diagnostic; source preserved'))
  env=dict(os.environ,NTNU_WAVE_AUDIT_OUT=str(A));state('exporting_saved_fields_CPU',source=str(source),workers=1,gpu=False)
  with (A/'star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-batch',str(A/'AuditWaveBackflow.java'),str(A/'input.sim')],cwd=str(A),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(A/'process.json',dict(launcher_pid=p.pid,gpu=False,workers=1))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   try:rc=p.wait(timeout=900)
   except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned zero-step audit exceeded900s')
   th.join(10)
  good=e.digest(source)==digest and e.digest(A/'input.sim')==digest
  result=dict(returncode=rc,source_unchanged=good,audit=e.read(A/'audit.json',{}),source=str(source),fields=str(A/'checkpoint_fields.csv'))
  e.write(A/'controller_result.json',result)
  if rc or not good or result['audit'].get('steps_taken')!=0:raise RuntimeError('Audit failed; inspect preserved logs')
  state('fields_ready_for_spatial_review',result=result,next='Locate velocity maximum, phase and boundary proximity; review water/interface separately before any longer continuation')
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  if claimed and e.read(cpu,{}).get('pid')==os.getpid():cpu.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
if __name__=='__main__':main()
