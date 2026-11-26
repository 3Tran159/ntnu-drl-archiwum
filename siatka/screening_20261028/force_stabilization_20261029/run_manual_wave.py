"""One fresh user-requested local run. Never resumes a failed state."""
import ctypes,json,os,shutil,subprocess,sys,threading,time,uuid
from pathlib import Path
import run_until_settled as e
import manual_control_common as c
R=c.R;W=c.W
def main():
 request=Path(sys.argv[1]).resolve()
 if request.parent!= (R/'manual_requests').resolve() or not request.name.endswith('.json'):raise ValueError('Invalid local request path')
 raw=c.read(request);cfg=c.validate_request({k:raw[k] for k in ('preset','target_s','wall_minutes')})
 pset=c.preset(cfg['preset']);source,sha=c.validate_source(pset)
 receipt=c.read(R/'manual_macro_build_receipt.json')
 if receipt.get('status')!='javac_passed' or c.digest(R/'ManualFoilWave.java')!=receipt.get('macro_sha256'):raise RuntimeError('Manual macro changed after compilation; rebuild required.')
 case=W/('MANUAL_'+pset['id']+'_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
 lock=R/'queue.lock';own=R/'manual_wave_controller.lock'
 if lock.exists() or own.exists() or (W/'preparation.lock').exists() or (R/'STOP_ALL').exists():raise RuntimeError('Campaign is locked or stopped; no launch.')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<20*1024**3:raise RuntimeError('Insufficient memory or E: space.')
 cmd="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'star' -and $_.CommandLine -match 'quasi2d_waves_20261029|force_stabilization_20261029'} | Select-Object -ExpandProperty ProcessId"
 probe=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
 if probe.returncode or probe.stdout.strip():raise RuntimeError('Campaign process observation is not clear; launch refused.')
 with request.with_suffix('.consumed').open('x') as f:f.write(e.stamp())
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='User-selected local dashboard run',case=case.name),f)
 proc=None
 def state(status,**kw):
  e.write(R/'wave_foil_run_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),gpu=True,workers=1,scope=pset['label']+'; manual exploratory run',formal_wave_force_acceptance=False,user_mass_exception=True,manual_request=cfg,**kw))
 try:
  with own.open('x') as f:json.dump(dict(pid=os.getpid(),case=case.name),f)
  case.mkdir();ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  state('manual_copying_prepared_input',progress={})
  shutil.copy2(source,case/'input.sim')
  if c.digest(case/'input.sim')!=sha:raise RuntimeError('Source copy hash mismatch.')
  shutil.copy2(R/'ManualFoilWave.java',case/'ManualFoilWave.java')
  e.write(case/'request.json',dict(**cfg,preset_definition=pset,requested_at=raw.get('requested_at'),request_file=str(request)))
  e.write(case/'source_identity.json',dict(source=str(source),source_sha256=sha,input_sha256=sha,source_time_s=0,source_cells=pset['cells'],source_is_guard_failed=False,height_m=pset['height'],wavelength_m=20,depth_m=24))
  (case/'README_INSPECTION.txt').write_text('Open final.sim after completion, or the last completed checkpoint. Inspect scenes 01-12: water fraction, alpha=0.5 surface, foil pressure/speed/instantaneous streamlines, outlet cells/phase residual/pressure/speed/streamlines. Per-cell MassImbalance is kg/s; use calibration records, do not volume-weight. Native MassConservationError is kg/step; divide by dt. Exploratory result, no final force-convergence claim. STOP requests save at a physical-step boundary. Never resume guard-failed fields. Each dashboard Start begins a fresh zero-time copy.\n',encoding='utf8')
  steps=round((cfg['target_s']-.02)/.001);wall=cfg['wall_minutes']*60
  env=dict(os.environ,NTNU_WAVE_OUT=str(case),NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS=str(steps),NTNU_WAVE_CELLS=str(pset['cells']),NTNU_WAVE_HEIGHT=str(pset['height']),NTNU_WAVE_WALL_S=str(wall))
  started=time.time();last_pt=0;last_change=started;last_update=0;reason=None
  with (case/'star.log').open('x',encoding='utf8') as log:
   proc=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(case/'ManualFoilWave.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   e.write(case/'process.json',dict(launcher_pid=proc.pid,started_at=e.stamp(),gpu=True,workers=1))
   def drain():
    for line in proc.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   while proc.poll() is None:
    now=time.time();elapsed=now-started;progress=e.read(case/'progress.json',{});pt=progress.get('time_s',0)
    if pt>last_pt:last_pt=pt;last_change=now
    stalled=(pt==0 and elapsed>900) or (pt>0 and now-last_change>600)
    memory=e.free_memory();disk=shutil.disk_usage(W).free
    if elapsed>wall or stalled or memory<8*1024**3 or disk<4*1024**3 or (R/'STOP_ALL').exists():
     (case/'STOP').touch()
     reason='wall_limit' if elapsed>wall else 'resource_or_progress_guard'
     e.write(case/'controller_stop_reason.json',dict(reason=reason,at=e.stamp()))
    if elapsed>wall+600 or memory<4*1024**3:
     subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError('Owned run exceeded saving grace or critical memory guard.')
    state('manual_wave_GPU_running',elapsed_s=elapsed,launcher_pid=proc.pid,progress=progress,stop_requested=(case/'STOP').exists())
    e.write(R/'queue_state.json',dict(status='running',active=case.name,updated_at=e.stamp(),purpose=pset['label']))
    if now-last_update>40:
     try:subprocess.run([sys.executable,str(R/'build_manual_dashboard_copy.py')],capture_output=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
     except Exception:pass
     last_update=now
    time.sleep(3)
   rc=proc.wait();th.join(10)
  done=e.read(case/'completed.json',{});preserved=c.digest(source)==sha and c.digest(case/'input.sim')==sha
  ok=rc==0 and preserved and done.get('status') in ('target_reached','stopped_by_marker','wall_budget')
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,elapsed_s=time.time()-started,stop_reason=reason)
  e.write(case/'controller_result.json',result);state('manual_run_saved_pending_review' if ok else 'needs_review',result=result,progress=done)
  e.write(R/'queue_state.json',dict(status='saved_pending_review' if ok else 'needs_review',active=None,updated_at=e.stamp()))
 except BaseException as ex:
  if proc is not None and proc.poll() is None:
   (case/'STOP').touch()
   try:proc.wait(timeout=180)
   except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state('needs_review',error=e.redact(str(ex)));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  for f in (own,lock):
   if e.read(f,{}).get('pid')==os.getpid():f.unlink()
if __name__=='__main__':
 try:main()
 except BaseException as ex:
  try:e.write(Path(sys.argv[1]).with_suffix('.error.json'),dict(error=e.redact(str(ex)),at=e.stamp()))
  except Exception:pass
  raise
