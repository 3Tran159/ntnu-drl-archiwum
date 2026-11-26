"""Fresh no-foil GPU pilot after the audited outlet-boundary correction. Never reuses failed flow."""
import os,sys,json,time,subprocess,threading,shutil,ctypes
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');srcdir=W/'W20_H24_X4_Q2D_r5';case=W/'W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3'
import run_until_settled as e
from mesh_selection_queue import running
lock=R/'queue.lock';own=R/'wave_flat_outlet_r3.lock'
def state(status,**kw):
 d=dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),workers=1,gpu=True,scope='Corrected-outlet no-foil pilot; not force or final propagation validation',**kw)
 for name in ['wave_propagation_state.json','wave_preparation_state.json']:
  try:e.write(R/name,d)
  except OSError as ex:
   with (case/'status_publish_errors.log').open('a') as f:f.write(e.stamp()+' '+str(ex)+'\n')
def main():
 if lock.exists() or own.exists():raise RuntimeError('Existing GPU owner; inspect before launch')
 if (W/'preparation.lock').exists() or running(38828) or running(28100) or running(15800) or running(36304):raise RuntimeError('Prior campaign or CPU pilot/audit still active')
 if e.read(R/'selected_mesh_decision.json',{}).get('status')!='supported_calm_mesh_template':raise RuntimeError('Calm mesh/time gate not passed')
 if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Insufficient pilot resources')
 if case.exists():raise RuntimeError('Attempt exists; preserve and use new ID')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Corrected-outlet FifthOrder no-foil GPU pilot r3'),f)
 with own.open('x') as f:json.dump(dict(pid=os.getpid(),case=case.name),f)
 p=None;claimed=True
 try:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  geo=e.read(srcdir/'topology_audit.json',{});audit=e.read(srcdir/'initial_audit.json',{})
  if geo.get('status')!='geometry_pass' or not geo.get('single_span') or not geo.get('boundary_mapping_valid'):raise RuntimeError('Independent geometry gate')
  if audit.get('depth_m')!=24 or audit.get('first_wave_front') is not False or audit['cells']!=53200:raise RuntimeError('Wave scope mismatch')
  case.mkdir();source=srcdir/'built.sim';shutil.copy2(source,case/'input.sim');shutil.copy2(R/'WavePropagationFlatOutletR3.java',case/'WavePropagationFlatOutletR3.java')
  digest=e.digest(source)
  if digest!=e.digest(case/'input.sim'):raise RuntimeError('Source copy mismatch')
  e.write(case/'source_identity.json',dict(source=str(source),source_sha256=digest,copied_sha256=digest,prior_failed_attempt='W20_H24_X4_CPUprop_dt1ms_r2',restart_from_failed_fields=False,change='Outlet pressure and phase use existing flat-wave reference; FifthOrder inlet/initialization and damping remain',hardware='One GPU versus prior CPU2; physics settings otherwise retained'))
  env=dict(os.environ,NTNU_WAVE_OUT=str(case),NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='1200',NTNU_WAVE_CELLS='53200')
  start=time.time();state('propagation_GPU_running',progress={})
  with (case/'star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(case/'WavePropagationFlatOutletR3.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   e.write(case/'process.json',dict(launcher_pid=p.pid,started_at=e.stamp(),gpu=True,workers=1))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start();last=0
   while p.poll() is None:
    elapsed=time.time()-start
    if elapsed>2900 or e.free_memory()<8*1024**3 or (R/'STOP_ALL').exists():(case/'STOP').touch()
    if elapsed>3300 or e.free_memory()<4*1024**3:
     subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned pilot exceeded resource/save grace')
    state('propagation_GPU_running',elapsed_s=elapsed,launcher_pid=p.pid,progress=e.read(case/'progress.json',{}))
    e.write(R/'queue_state.json',dict(status='running',active=case.name,updated_at=e.stamp(),purpose='Fifth-order no-foil outlet correction pilot',waves_blocked_until_wave_checks=True))
    if time.time()-last>30:
     try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
     except Exception:pass
     last=time.time()
    time.sleep(10)
   rc=p.wait();th.join(10)
  done=e.read(case/'completed.json',{});preserved=e.digest(source)==digest and e.digest(case/'input.sim')==digest
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,elapsed_s=time.time()-start)
  e.write(case/'controller_result.json',result)
  status='propagation_pilot_complete_pending_review' if rc==0 and preserved and done.get('status')=='target_reached' and done.get('steps')==1200 else 'needs_review'
  state(status,result=result,next='Check outlet spatial fields, full-cycle gauges, mean level and conservation; reflection and timestep checks still pending')
  e.write(R/'queue_state.json',dict(status=status,updated_at=e.stamp(),active=None,purpose='No-foil pilot ended; scientific review before continuation'))
 except BaseException as ex:
  if p is not None and p.poll() is None:
   (case/'STOP').touch()
   try:p.wait(timeout=90)
   except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state('needs_review',error=str(ex));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
  try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
  except Exception:pass
if __name__=='__main__':main()
