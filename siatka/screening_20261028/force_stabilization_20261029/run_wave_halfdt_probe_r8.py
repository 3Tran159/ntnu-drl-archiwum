"""Investigate R4 mass spikes withhalfdt10inner; R6twentyinner failed.01%gate; longcontinuation staysgated."""
import os,sys,json,time,subprocess,threading,shutil,ctypes
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');srcdir=W/'W20_H24_X4_Q2D_r5';case=W/'W20_H24_X4_GPUprop_environmentalOutlet_halfdt10inner_r8'
import run_until_settled as e
from mesh_selection_queue import running
lock=R/'queue.lock';own=R/'wave_halfdt_probe_r8.lock'
def state(status,**kw):
 d=dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),workers=1,gpu=True,scope='Environmental outlet and slip bed no-foil pilot; not force or final propagation validation',**kw)
 for name in ['wave_propagation_state.json','wave_preparation_state.json']:
  try:e.write(R/name,d)
  except OSError as ex:
   with (case/'status_publish_errors.log').open('a') as f:f.write(e.stamp()+' '+str(ex)+'\n')
def main():
 if lock.exists() or own.exists():raise RuntimeError('Existing GPU owner; inspect before launch')
 if running(36724):raise RuntimeError('Prior GPU pilot still active')
 cpu=e.read(W/'preparation.lock',{})
 if cpu and cpu.get('purpose')!='Paired foil calm/W01 zero-step CPU1 preparation':raise RuntimeError('Other CPU owner; inspect resources first')
 if e.read(R/'selected_mesh_decision.json',{}).get('status')!='supported_calm_mesh_template':raise RuntimeError('Calm mesh/time gate not passed')
 if (R/'STOP_ALL').exists():raise RuntimeError('User stop marker')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Insufficient pilot resources')
 prior=e.read(W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'controller_result.json',{})
 review=e.read(R/'wave_pilot_r4_review.json',{});sp=e.read(R/'wave_pilot_r4_spatial_diagnostic.json',{})
 if not prior.get('source_unchanged') or prior.get('completed',{}).get('status')!='target_reached' or prior.get('completed',{}).get('steps')!=1200:raise RuntimeError('R4 not completed safely')
 if not review.get('independent_histories_finite') or not sp.get('all_fields_finite'):raise RuntimeError('R4 independent review absent')
 if sp['max_speed']['speed_m_s']>25:raise RuntimeError('R4 spatial diagnostic requires investigation')
 # This short probe investigates the failed0.01%mass gate; it does not authorize longer propagation.
 if max(x['RMS_error_mm'] for x in review['gauges'])>10 or max(x['max_error_mm'] for x in review['gauges'])>20:raise RuntimeError('R4 gauge mismatch too large for longer continuation')
 if case.exists():raise RuntimeError('Attempt exists; preserve and use new ID')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Environmental outlet and slip bed FifthOrder no-foil GPU halfdt10inner diagnostic r8'),f)
 try:
  with own.open('x') as f:json.dump(dict(pid=os.getpid(),case=case.name),f)
 except BaseException:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  raise
 p=None;claimed=True
 try:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  geo=e.read(srcdir/'topology_audit.json',{});audit=e.read(srcdir/'initial_audit.json',{})
  if geo.get('status')!='geometry_pass' or not geo.get('single_span') or not geo.get('boundary_mapping_valid'):raise RuntimeError('Independent geometry gate')
  if audit.get('depth_m')!=24 or audit.get('first_wave_front') is not False or audit['cells']!=53200:raise RuntimeError('Wave scope mismatch')
  case.mkdir();source=W/'W20_H24_X4_GPUprop_environmentalOutlet_dt1ms_r4'/'checkpoint_t0.500.sim';shutil.copy2(source,case/'input.sim');shutil.copy2(R/'WaveHalfDtProbeR8.java',case/'WaveHalfDtProbeR8.java')
  digest=e.digest(source)
  if digest!=e.digest(case/'input.sim'):raise RuntimeError('Source copy mismatch')
  e.write(case/'source_identity.json',dict(source=str(source),source_sha256=digest,copied_sha256=digest,prior_failed_attempt='W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3',restart_from='r4 t0.500 checkpoint, matched to10innerhistory',restart_from_failed_fields=False,change='Matched0.500to0.750s diagnostic;1ms to0.5ms only versusR4,10inner andallBCs unchanged,no reinitialization',hardware='OneGPU, sameasR4; timestep only'))
  env=dict(os.environ,NTNU_WAVE_OUT=str(case),NTNU_WAVE_DT='.0005',NTNU_WAVE_STEPS='500',NTNU_WAVE_CELLS='53200')
  start=time.time();state('propagation_GPU_running',progress={})
  with (case/'star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(case/'WaveHalfDtProbeR8.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
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
    e.write(R/'queue_state.json',dict(status='running',active=case.name,updated_at=e.stamp(),purpose='Fifth-order no-foil environmental outlet and slip bed pilot',waves_blocked_until_wave_checks=True))
    if time.time()-last>30:
     try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
     except Exception:pass
     last=time.time()
    time.sleep(10)
   rc=p.wait();th.join(10)
  done=e.read(case/'completed.json',{});preserved=e.digest(source)==digest and e.digest(case/'input.sim')==digest
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,elapsed_s=time.time()-start)
  e.write(case/'controller_result.json',result)
  status='propagation_pilot_complete_pending_review' if rc==0 and preserved and done.get('status')=='target_reached' and done.get('steps')==500 else 'needs_review'
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
