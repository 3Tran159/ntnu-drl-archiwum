"""Authorized first foil-wave trial. Sequential GPU; source copies preserved."""
import ctypes,datetime,json,os,shutil,subprocess,sys,threading,time
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
case=W/'W01_W20L4_M10_FS020_diagnostic_r1'
source=W/'W01_W20L4_M10_FS020_env_setup_r1'/'prepared.sim'
lock=R/'queue.lock';own=R/'first_foil_wave_diagnostic_r1.lock'
def state(status,**kw):
 e.write(R/'wave_foil_run_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),workers=1,gpu=True,scope='W01 foil-wave diagnostic: H0.5m L20m depth24m, M10 FS020 317277cells; native scenes and outlet diagnostics; exploratory forces',**kw))
def main():
 if lock.exists() or own.exists():raise RuntimeError('GPU queue owned; inspect before any launch')
 if (W/'preparation.lock').exists():raise RuntimeError('CPU preparation owner present; inspect before launch')
 auth=e.read(R/'first_foil_wave_authorization_20261030.json',{})
 if auth.get('status')!='explicit_user_authorized' or not auth.get('observed_mass_deviation_accepted_for_exploration'):raise RuntimeError('Explicit exploratory authorization missing')
 if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker remains; do not bypass')
 if case.exists():raise RuntimeError('Attempt already exists; preserve and use a new ID')
 inputs=e.read(R/'wave_fs_case_preparation_results.json',{})
 records=[v for v in inputs.get('results',[]) if v.get('case')=='W01_W20L4_M10_FS020_env_setup_r1']
 if len(records)!=1:raise RuntimeError('Unique prepared input evidence missing')
 record=records[0];audit=record.get('audit',{})
 if record.get('source_unchanged') is not True or record.get('returncode')!=0 or audit.get('status')!='prepared_zero_steps' or audit.get('flow_steps')!=0 or audit.get('cells')!=317277 or audit.get('wave_class')!='FifthOrderVofWave':raise RuntimeError('Prepared source audit not passed')
 if audit.get('settings',{}).get('water_depth_m')!=24 or audit['settings'].get('bottom')!='SLIP' or audit['settings'].get('outlet_pressure')!='ENVIRONMENTAL':raise RuntimeError('Scope or boundary mismatch')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<12*1024**3:raise RuntimeError('Insufficient resources; preserve other work')
 # Identify our campaign solvers only; unrelated HF session is not controlled.
 ps=r"Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'star' -and $_.CommandLine -match 'quasi2d_waves_20261029|force_stabilization_20261029'} | Select-Object -ExpandProperty ProcessId"
 active=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
 if active.returncode or active.stdout.strip():raise RuntimeError('Campaign solver observation not clear; no duplicate launch')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='First authorized W01 foil wave with outlet diagnostics and native inspection scenes'),f)
 try:
  with own.open('x') as f:json.dump(dict(pid=os.getpid(),case=case.name),f)
 except BaseException:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  raise
 p=None
 try:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  case.mkdir();state('copying_prepared_foil_wave_input')
  digest=e.digest(source);shutil.copy2(source,case/'input.sim');shutil.copy2(R/'FoilWaveDiagnosticR1.java',case/'FoilWaveDiagnosticR1.java')
  if e.digest(case/'input.sim')!=digest:raise RuntimeError('Source copy hash mismatch')
  e.write(case/'source_identity.json',dict(source=str(source),source_sha256=digest,input_sha256=digest,source_time_s=0,source_cells=317277,case='W01',wave_height_m=.5,wavelength_m=20,depth_m=24,source_is_guard_failed=False,initialization='Prepared fifth-order initialized source; no reinitialization',authorization='first_foil_wave_authorization_20261030.json'))
  shutil.copy2(R/'first_foil_wave_authorization_20261030.json',case/'authorization.json')
  (case/'README_INSPECTION.txt').write_text('W01 H0.5m L20m H24m, M10 FS020, 317277 cells.\nOpen inspection_setup.sim for zero-time setup, or the newest completed checkpoint/final.sim for flow fields.\nScenes W01 01-12: whole tank alpha; alpha0.5 free surface; foil pressure/speed/instantaneous streamlines; outlet alpha/mesh, water+air residual, pressure/speed/streamlines; free-surface close-up.\nMonitors/plots contain independent slice forces, native phase error (kg/step) and outlet-column imbalance (kg/s). Divide native kg/step by current dt for comparison. Do not multiply per-cell kg/s by cell volume.\nOutlet cell/face CSVs sample evolving fields. Full local_balance snapshots calibrate cell sums against native phase reports.\nThis is an exploratory first wave run. User accepts previous~0.0143% mass deviation; original0.01% is still flagged and recorded. No final wave-force accuracy/reflection/grid/time convergence claim.\nNever continue guard_or_error_preserved.sim after physical instability.\n',encoding='utf8')
  env=dict(os.environ,NTNU_WAVE_OUT=str(case),NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='1180',NTNU_WAVE_CELLS='317277')
  start=time.time();last_update=0;last_progress_time=0;last_progress_wall=start
  state('foil_wave_GPU_starting',progress={})
  with (case/'star.log').open('x',encoding='utf8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(case/'FoilWaveDiagnosticR1.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   e.write(case/'process.json',dict(launcher_pid=p.pid,started_at=e.stamp(),gpu=True,workers=1))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   while p.poll() is None:
    elapsed=time.time()-start;progress=e.read(case/'progress.json',{});pt=progress.get('time_s',0)
    if pt>last_progress_time:last_progress_time=pt;last_progress_wall=time.time()
    stalled=(elapsed>900 and pt==0) or (pt>0 and time.time()-last_progress_wall>600)
    if elapsed>7800 or stalled or e.free_memory()<8*1024**3 or shutil.disk_usage(W).free<4*1024**3 or (R/'STOP_ALL').exists():(case/'STOP').touch()
    if elapsed>8400 or e.free_memory()<4*1024**3:
     subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned attempt exceeded resource/save grace')
    state('foil_wave_GPU_running',elapsed_s=elapsed,launcher_pid=p.pid,progress=progress,user_mass_exception=True,formal_wave_force_acceptance=False)
    e.write(R/'queue_state.json',dict(status='running',active=case.name,updated_at=e.stamp(),purpose='Exploratory W01 with outlet diagnosis and saved inspection scenes'))
    if time.time()-last_update>35:
     try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW)
     except Exception:pass
     last_update=time.time()
    time.sleep(10)
   rc=p.wait();th.join(10)
  done=e.read(case/'completed.json',{});preserved=e.digest(source)==digest and e.digest(case/'input.sim')==digest
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,elapsed_s=time.time()-start)
  e.write(case/'controller_result.json',result)
  status='foil_wave_trial_complete_pending_review' if rc==0 and preserved and done.get('status')=='target_reached' and done.get('steps')==1180 else 'needs_review'
  state(status,result=result,next='Review startup, phase/native budget, outlet fields and foil forces. First1.2s is diagnostic; then controlled extension to complete cycles and matched calm reference.')
  e.write(R/'queue_state.json',dict(status=status,active=None,updated_at=e.stamp(),purpose='First foil wave trial finished; saved scenes and diagnostics'))
 except BaseException as ex:
  if p is not None and p.poll() is None:
   (case/'STOP').touch()
   try:p.wait(timeout=120)
   except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state('needs_review',error=e.redact(str(ex)));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
if __name__=='__main__':main()
