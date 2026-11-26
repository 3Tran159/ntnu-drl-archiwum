"""Unique W01a inlet-wave run from computed calm checkpoint; no global reinitialization."""
import ctypes,json,os,shutil,subprocess,sys,threading,time
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent
W=Path('E:/ntnu/quasi2d_waves_20261029')
CASE=W/'W01a_W20L4_M10_inlet_fullheight_restart_r3'
SOURCE=W/'C01_W20L4_M10_FS020_env_setup_r1/prepared.sim'
MACRO=R/'W01aFullHeightRestartR3.java'
LOCK=R/'queue.lock';OWN=R/'w01a_fullheight_restart_r3.lock'
WALL=50400
def main():
 if sys.argv[1:]!=['--run']:raise RuntimeError('Use explicit --run only after audit review')
 audit=e.read(SOURCE.parent/'initial_audit.json',{})
 if audit.get('status')!='prepared_zero_steps' or audit.get('time_s')!=0 or audit.get('flow_steps')!=0 or audit.get('cells')!=317277 or audit.get('wave')!=False:raise RuntimeError('Verified zero-time calm input required')
 source_sha=e.digest(SOURCE)
 if source_sha!='8cab371c1f4bd000283877b4e28811c978814cc30a57c9fb7701cce85fc235ce':raise RuntimeError('Prepared source identity differs')
 prior=e.read(W/'W01a_W20L4_M10_inlet_wave_r1/controller_result.json',{})
 if prior.get('returncode')!=0 or prior.get('source_unchanged')!=True or prior.get('completed',{}).get('status')!='stopped_by_marker':raise RuntimeError('Previous ramp attempt not saved normally')
 if CASE.exists():raise RuntimeError('Unique attempt already exists; preserve and use new ID')
 receipt=e.read(R/'w01a_fullheight_r3_macro_build_receipt.json',{})
 if receipt.get('status')!='javac_passed' or e.digest(MACRO)!=receipt.get('macro_sha256'):raise RuntimeError('Macro compile identity mismatch')
 if any(p.exists() for p in [LOCK,OWN,W/'preparation.lock',R/'STOP_ALL']):raise RuntimeError('Existing lock or stop: no launch')
 cmd="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'star' -and $_.CommandLine -match 'quasi2d_waves_20261029|force_stabilization_20261029'} | Select-Object -ExpandProperty ProcessId"
 q=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
 if q.returncode or q.stdout.strip():raise RuntimeError('Existing campaign STAR process or failed process audit')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<25*1024**3:raise RuntimeError('Insufficient resources')
 with LOCK.open('x') as f:json.dump(dict(pid=os.getpid(),case=CASE.name,purpose='W01a immediate inlet-generated wave from fresh t0 full-height H0.5'),f)
 proc=None
 def state(status,**kw):
  activation=e.read(CASE/'wave_activation.json',{})
  e.write(R/'wave_foil_run_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=CASE.name,directory=str(CASE),gpu=True,workers=1,scope='W01a inlet-generated FifthOrder H.5 L20 depth24; constant H0.5 from t0, no height ramp, no calm-force wait or global initialization',computation_stage=activation.get('stage','inlet_wave_loading'),activation=activation,source_time_s=0,formal_wave_force_acceptance=False,user_mass_exception=True,**kw))
 try:
  with OWN.open('x') as f:json.dump(dict(pid=os.getpid(),case=CASE.name),f)
  CASE.mkdir()
  state('W01a_copying_computed_checkpoint',computation_active=False,progress={'time_s':0})
  shutil.copy2(SOURCE,CASE/'input.sim')
  if e.digest(CASE/'input.sim')!=source_sha:raise RuntimeError('Copy hash mismatch')
  shutil.copy2(MACRO,CASE/MACRO.name)
  e.write(CASE/'source_identity.json',dict(source=str(SOURCE),source_sha256=source_sha,input_sha256=source_sha,source_time_s=0,source_cells=317277,source_is_guard_failed=False,source_calm_settled=False,height_m=.5,wavelength_m=20,depth_m=24))
  e.write(CASE/'request.json',dict(requested_at=e.stamp(),user_instruction='Restart W01a from t0 with inlet H0.5 from first step, no height ramp or force settling wait; clear old live dashboard history',target_s=18.429,wall_minutes=840,minimum_repeated_cycles=4,typical_cycles=10,review_cap_cycles=20,no_global_wave_initialization=True))
  (CASE/'README_INSPECTION.txt').write_text('W01a fresh t0 restart. Full H0.5 wave at inlet/upstream forcing from first .5ms guarded step; NO height ramp or calm waiting. Initial interior fields remain calm. First40steps .5ms50inner, thenSO1ms10inner. Original calm and old failed W01 sources preserved. Native scenes include water fraction, alpha=.5 surface, pressure, speed, streamlines, phase residuals and signed omega_y vorticity (1/s). Open final.sim or latest_checkpoint.json completed file; input.sim is zero-step initialized calm template; computed results are separate completed checkpoints. No final accuracy claim. STOP requests safe save after current step. Do not continue a stability-guard failed state.\n',encoding='utf8')
  k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
  if not k.SetProcessAffinityMask(k.GetCurrentProcess(),3):raise RuntimeError('Cannot set own CPU0/1 affinity')
  k.SetThreadExecutionState(0x80000001)
  started=time.time();last_pt=0;last_change=started;last_ui=0;reason=None
  with (CASE/'star.log').open('x',encoding='utf8') as log:
   proc=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(CASE/MACRO.name),str(CASE/'input.sim')],cwd=str(CASE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   e.write(CASE/'process.json',dict(launcher_pid=proc.pid,started_at=e.stamp(),gpu=True,workers=1,cpu_affinity_mask=3))
   def drain():
    for line in proc.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   state('W01a_inlet_GPU_loading',computation_active=True,launcher_pid=proc.pid,progress={'time_s':0})
   while proc.poll() is None:
    now=time.time();elapsed=now-started;progress=e.read(CASE/'progress.json',{'time_s':0});pt=progress.get('time_s',0)
    if pt>last_pt:last_pt=pt;last_change=now
    memory=e.free_memory();disk=shutil.disk_usage(W).free
    stalled=(pt<=0 and elapsed>900) or (pt>0 and now-last_change>600)
    if elapsed>WALL or stalled or memory<8*1024**3 or disk<4*1024**3 or (R/'STOP_ALL').exists():
     (CASE/'STOP').touch();reason='wall_limit' if elapsed>WALL else 'resource_or_progress_guard'
     e.write(CASE/'controller_stop_reason.json',dict(reason=reason,at=e.stamp()))
    if elapsed>WALL+600 or memory<4*1024**3:
     subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError('Owned process exceeded save grace or critical memory')
    state('W01a_inlet_GPU_running' if pt>0 else 'W01a_inlet_GPU_loading',computation_active=True,elapsed_s=elapsed,launcher_pid=proc.pid,progress=progress,stop_requested=(CASE/'STOP').exists())
    e.write(R/'queue_state.json',dict(status='running',active=CASE.name,updated_at=e.stamp(),purpose='W01a inlet-generated wave'))
    if now-last_ui>45:
     try:subprocess.run([sys.executable,str(R/'build_manual_dashboard_copy.py')],capture_output=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
     except Exception:pass
     last_ui=now
    time.sleep(3)
   rc=proc.wait();th.join(10)
  done=e.read(CASE/'completed.json',{})
  preserved=e.digest(SOURCE)==source_sha and e.digest(CASE/'input.sim')==source_sha
  ok=rc==0 and preserved and done.get('status') in ('target_reached','stopped_by_marker','wall_budget')
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,elapsed_s=time.time()-started,stop_reason=reason)
  e.write(CASE/'controller_result.json',result);state('W01a_inlet_saved_pending_review' if ok else 'needs_review',computation_active=False,result=result,progress=done)
  e.write(R/'queue_state.json',dict(status='saved_pending_review' if ok else 'needs_review',active=None,updated_at=e.stamp()))
 except BaseException as ex:
  if proc is not None and proc.poll() is None:
   (CASE/'STOP').touch()
   try:proc.wait(timeout=180)
   except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state('needs_review',computation_active=False,error=e.redact(str(ex)));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  for p in [OWN,LOCK]:
   if e.read(p,{}).get('pid')==os.getpid():p.unlink()
if __name__=='__main__':main()
