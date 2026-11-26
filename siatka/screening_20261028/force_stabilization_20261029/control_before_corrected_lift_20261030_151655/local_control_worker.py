"""Standalone local queue: new attempts only, one owned solver, no dependency on Work."""
from pathlib import Path
import os,sys,json,time,uuid,shutil,subprocess,threading,csv,math,ctypes,statistics
import local_control_model as m
import local_domain_preparation as domain
import autonomous_wave_campaign as audit
import wave_cycle_repeatability as cycles
import local_wave_arrival as arrival
import run_until_settled as e
R=m.R;W=m.W;D=m.D
class Halt(RuntimeError):pass
class Cancelled(Halt):pass
def ensure_not_cancelled(j):
 if (D/'jobs'/j['id']/'CANCEL').exists() or m.read(D/'jobs'/j['id']/'job.json').get('status')=='cancelled':raise Cancelled('Cancelled before next phase')
def calm_screen(path,dt=.001):
 rows,bad=audit.force_rows(path);out={'pass':False,'window_s':.2,'limit_pct':.5,'invalid_rows':bad,'denominator':'absolute_latest_mean'}
 if bad or len(rows)<round(.4/dt):return dict(out,reason='Two complete 0.2s windows required')
 times=[r['time_s'] for r in rows];t=times[-1]
 if any(b<=a for a,b in zip(times,times[1:])):return dict(out,reason='Non-monotonic history')
 if t-times[0]<.4-1e-9:return dict(out,reason='At least0.4s new-setting history required')
 selected=[r for r in rows if t-.4-1e-9<=r['time_s']<=t+1e-10]
 if any(b['time_s']-a['time_s']>dt*1.01 for a,b in zip(selected,selected[1:])):return dict(out,reason='History gap')
 previous=[r for r in rows if t-.4<r['time_s']<=t-.2]
 current=[r for r in rows if t-.2<r['time_s']<=t+1e-10]
 if min(len(previous),len(current))<round(.2/dt)-1:return dict(out,reason='Insufficient time-step samples in a 0.2s window')
 values={}
 for key in ('CD','CL_total'):
  a=statistics.mean(r[key] for r in previous);b=statistics.mean(r[key] for r in current)
  change=100*(b-a)/abs(b) if abs(b)>1e-12 else None
  values[key]=dict(previous_mean=a,mean=b,change_pct=change)
 components={}
 for key in ('pressure_drag_N','viscous_drag_N','Fx_slice_N','Fz_slice_N'):
  v=[audit.number(r.get(key)) for r in current]
  if v and all(x is not None for x in v):components[key]=statistics.mean(v)
 return dict(out,**{'pass':all(v['change_pct'] is not None and abs(v['change_pct'])<.5 for v in values.values()),'time_s':t,'end_s':t,'windows_s':[[t-.4,t-.2],[t-.2,t]],'previous_window_s':[t-.4,t-.2],'current_window_s':[t-.2,t],'coefficients':values,'mean_force_components_N':components,'samples':[len(previous),len(current)]})
def pause():return (D/'PAUSE').exists() or (R/'STOP_ALL').exists() or m.hold().get('active',False)
def resources():return e.free_memory(),shutil.disk_usage(W).free
def own_lock(p,token,case=None):
 with p.open('x') as f:json.dump(dict(pid=os.getpid(),token=token,case=case,created_at=m.stamp()),f)
def release(p,token):
 v=m.read(p)
 if v.get('pid')==os.getpid() and v.get('token')==token:p.unlink()
def status(j,text,**kw):
 if kw.get('status')!='cancelled':ensure_not_cancelled(j)
 j.update(updated_at=m.stamp(),message=text,**kw);m.write(D/'jobs'/j['id']/'job.json',j);m.write(D/'state.json',dict(job=j['id'],status=j['status'],message=text,updated_at=m.stamp(),pid=os.getpid()))
def safe_ready():
 if (R/'queue.lock').exists() or (W/'preparation.lock').exists():return False
 command="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'star' -and $_.CommandLine -and ($_.CommandLine.Replace([char]92,[char]47) -match 'E:/ntnu/quasi2d_waves_20261029/|F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/')} | Select-Object -ExpandProperty ProcessId"
 p=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
 if p.returncode:raise Halt('Cannot verify solver process inventory')
 return not p.stdout.strip()
def stop_report(j,reason):
 diagnostic=dict(error_type='controller_review_required',message=reason,updated_at=m.stamp())
 if j.get('attempts'):
  folder=Path(j['attempts'][-1]['directory']);done=m.read(folder/'completed.json');rows=[]
  try:rows=audit.csv_rows(folder/'history.csv')
  except (OSError,ValueError):pass
  last=rows[-1] if rows else {}
  if done.get('status')=='stability_guard':diagnostic['error_type']='physical_stability_guard'
  elif 'Native' in reason:diagnostic['error_type']='diagnostic_sampling_failure'
  elif 'identity' in reason.lower() or 'source' in reason.lower():diagnostic['error_type']='source_identity_failure'
  elif 'memory' in reason.lower() or 'storage' in reason.lower():diagnostic['error_type']='resource_limit'
  diagnostic.update(case=folder.name,physical_time_s=done.get('time_s',audit.number(last.get('time_s'))),completed_status=done.get('status'),last_sample=last,diagnostic_file=str(folder/'final.sim') if (folder/'final.sim').is_file() else None,history_file=str(folder/'history.csv'),native=audit.native_audit(folder,done.get('steps',0)) if done else {})
  m.write(folder/'diagnostic_summary.json',diagnostic)
 status(j,reason,status='needs_review',diagnostics=diagnostic);(D/'PAUSE').touch()

def execute_solver(j,mode,source):
 ensure_not_cancelled(j)
 if pause():raise Halt('Queue paused; no new solver launch')
 s=j['spec'];t0=source.get('physical_time_s',0);token=uuid.uuid4().hex;dt=s['dt_s'];resuming=source.get('status')=='safe_saved_continuation';activation_t=source.get('activation_time_s',t0)
 selected=m.mesh_profile(s['mesh_id'])
 if selected['file_sha256']!=s['mesh_sha256']:raise Halt('Inspected mesh identity changed; create a new job')
 if isinstance(t0,bool) or not isinstance(t0,(int,float)) or not math.isfinite(t0) or t0<0 or (mode!='calm' and t0<=0):raise Halt('Invalid source physical time')
 phase='C01' if mode=='calm' else 'WAVE_SETUP' if mode=='wave_setup' else s['name'].replace(' ','_')
 folder=W/('LOCAL_'+j['id']+'_'+mode+'_'+uuid.uuid4().hex[:6])
 if not safe_ready():raise Halt('Another solver/preparation holds the campaign; no duplicate')
 if min(resources())<24*1024**3:raise Halt('Need24GiB RAM and storage before launch')
 receipt=m.read(R/'local_control_macro_receipt.json');macro=R/'LocalCalmWave.java'
 if receipt.get('status')!='javac_passed' or e.digest(macro)!=receipt.get('macro_sha256'):raise Halt('Local macro compile identity changed')
 psrc=Path(source.get('file',source.get('path','missing')))
 if not psrc.resolve().is_relative_to(W.resolve()) or not psrc.is_file() or e.digest(psrc)!=source['sha256']:raise Halt('Source identity mismatch')
 if mode!='calm' and (source.get('status') not in ('calm_force_settled','safe_saved_continuation') or not source.get('source_unchanged')):raise Halt('A matching settled C01 or verified continuation is required')
 if resuming and (source.get('physical_guard_failed') is not False or source.get('mode')!=mode or source.get('domain_key')!=m.domain_key(s) or source.get('dt_s')!=dt):raise Halt('Continuation profile or guard mismatch')
 if resuming and mode=='wave':
  if isinstance(activation_t,bool) or not isinstance(activation_t,(int,float)) or not math.isfinite(activation_t) or not 0<=activation_t<=t0:raise Halt('Invalid inherited wave activation time')
  inherited_period=source.get('period_s')
  if inherited_period is not None and (isinstance(inherited_period,bool) or not isinstance(inherited_period,(int,float)) or not math.isfinite(inherited_period) or inherited_period<=0):raise Halt('Invalid inherited wave period')
  established=source.get('arrival_assessment') or {}
  origin=established.get('analysis_origin_s')
  if established.get('established') and (inherited_period is None or isinstance(origin,bool) or not isinstance(origin,(int,float)) or not math.isfinite(origin) or not activation_t<=origin<=t0):raise Halt('Invalid inherited analysis clock')
  for filename in source.get('history_files',[]):
   hp=Path(filename)
   if not hp.resolve().is_relative_to(W.resolve()) or not hp.is_file() or e.digest(hp)!=source.get('history_sha256',{}).get(filename):raise Halt('Inherited force history changed')

 lock=R/'queue.lock';proc=None;started=time.monotonic();stop_at=None;reason=None
 try:
  ensure_not_cancelled(j)
  if pause():raise Halt('Queue paused before solver claim')
  with m.job_transition(j['id']):
   ensure_not_cancelled(j)
   own_lock(lock,token,folder.name);folder.mkdir()
   j['attempts'].append(dict(mode=mode,directory=str(folder),source=str(psrc),source_time_s=t0));status(j,'Loading '+phase+' from verified saved state',status='running')
  shutil.copy2(psrc,folder/'input.sim')
  if e.digest(folder/'input.sim')!=source['sha256']:raise Halt('Disposable input copy mismatch')
  shutil.copy2(macro,folder/macro.name)
  m.write(folder/'source_identity.json',dict(source=str(psrc),source_sha256=source['sha256'],input_sha256=source['sha256'],source_time_s=t0,source_cells=source['cells'],source_calm_settled=mode!='calm' and not resuming,source_is_guard_failed=False,reinitialized=False,height_m=0 if mode=='calm' else s['height_m'],wavelength_m=s['wavelength_m'],mesh=source.get('mesh'),spec=s,resume_wave=resuming and mode=='wave',continuation_mode=mode if resuming else None,history_files=source.get('history_files',[]) if resuming else [],history_sha256=source.get('history_sha256',{}) if resuming else {},activation_time_s=activation_t))
  m.write(folder/'request.json',dict(job=j['id'],mode=mode,spec=s,source_manifest=source.get('manifest'),created_at=m.stamp()))
  remaining=6-t0 if mode=='calm' else 40
  startup_duration=40*min(dt,.0005) if t0==0 else 0
  steps=round((remaining-startup_duration)/dt)
  if steps<30:raise Halt('Calm time cap reached before settling; inspect existing reference')
  gauges=sorted(set([s['xmin_m']+1,s['xmin_m']+s['zone_m']-.5,-1.,2.5,5.,s['xmax_m']-s['zone_m']+.5,s['xmax_m']-1]))
  env=dict(os.environ,NTNU_WAVE_OUT=str(folder),NTNU_MODE=mode,NTNU_SOURCE_TIME=str(t0),NTNU_WAVE_DT=str(dt),NTNU_WAVE_STEPS=str(steps),NTNU_WAVE_CELLS=str(source['cells']),NTNU_WAVE_HEIGHT=str(0 if mode=='calm' else s['height_m']),NTNU_WAVE_WALL_S=str(s['wall_minutes']*60),NTNU_CFG_XMIN=str(s['xmin_m']),NTNU_CFG_XMAX=str(s['xmax_m']),NTNU_CFG_LAMBDA=str(s['wavelength_m']),NTNU_CFG_GAUGES=','.join(map(str,gauges)),NTNU_ZONE=str(s['zone_m']),NTNU_CHECKPOINT_INTERVAL_S=str(s.get('checkpoint_interval_s',.05)),NTNU_RESUME_WAVE=str(resuming and mode=='wave').lower(),NTNU_WAVE_ACTIVATION_TIME=str(activation_t))
  cmd=[str(e.STAR),*e.saved_options(1)]+([] if mode=='wave_setup' else ['-gpgpu','auto:1'])+['-batch',str(folder/macro.name),str(folder/'input.sim')]
  with (folder/'star.log').open('x',encoding='utf-8') as log:
   ensure_not_cancelled(j)
   if pause():raise Halt('Queue paused before STAR launch')
   proc=subprocess.Popen(cmd,cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   m.write(folder/'process.json',dict(launcher_pid=proc.pid,controller_pid=os.getpid(),mode=mode,gpu=mode!='wave_setup',started_at=m.stamp()))
   def drain():
    for line in proc.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   last_t=t0;last_change=time.monotonic();last_eval=0;period=source.get('period_s') if resuming else None;arrival_result=source.get('arrival_assessment') if resuming else None;decision={}
   if period is not None:m.write(folder/'frozen_period.json',dict(period_s=period,activation_time_s=activation_t,inherited=True))
   while proc.poll() is None:
    now=time.monotonic();progress=m.read(folder/'progress.json');t=progress.get('time_s',t0)
    if t>last_t:last_t=t;last_change=now
    stage='calm_settling' if mode=='calm' else 'wave_setup' if mode=='wave_setup' else 'inlet_wave_full_amplitude'
    activation=m.read(folder/'wave_activation.json')
    if arrival_result and arrival_result.get('established'):activation['analysis_origin_s']=arrival_result['analysis_origin_s']
    m.write(R/'wave_foil_run_state.json',dict(status='local_'+mode+'_running',case=folder.name,directory=str(folder),controller_pid=os.getpid(),launcher_pid=proc.pid,updated_at=m.stamp(),gpu=mode!='wave_setup',workers=1,scope=s['name']+'; matching settled C01 then full-height inlet wave; no ramp',computation_stage=stage,source_time_s=t0,dt_s=dt,mesh_id=s['mesh_id'],history_sources=source.get('history_files',[]) if resuming else [],history_source_sha256=source.get('history_sha256',{}) if resuming else {},activation=activation,progress=progress,computation_active=True,stop_requested=(folder/'STOP').exists(),manual_request=dict(target_s=6 if mode=='calm' else t0+remaining,wall_minutes=s['wall_minutes']),formal_wave_force_acceptance=False,user_mass_exception=True))
    mem,disk=resources()
    issue='User paused queue' if pause() else 'Wall-time limit' if now-started>s['wall_minutes']*60 else 'Insufficient memory/storage' if mem<8*1024**3 or disk<8*1024**3 else 'No progress' if now-last_change>(900 if last_t==t0 else 600) else None
    if issue and reason is None:reason=issue;(folder/'STOP').touch()
    if (folder/'STOP').exists() and stop_at is None:stop_at=now
    if stop_at and now-stop_at>600:
     subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise Halt('Owned solver exceeded600s save grace; attempt preserved')
    if now-last_eval>=5 and (folder/'history.csv').exists() and reason is None and not (folder/'STOP').exists():
     last_eval=now;problem=audit.history_guard(folder/'history.csv')
     if problem:reason=problem;(folder/'STOP').touch()
     elif mode=='calm':
      screen=calm_screen(folder/'history.csv',dt)
      m.write(folder/'calm_settling.json',dict(screen,passed=screen.get('pass'),changes_pct={k:v['change_pct'] for k,v in screen.get('coefficients',{}).items()}))
      if screen.get('pass'):reason='calm_settled';decision=screen;(folder/'STOP').touch()
     elif mode=='wave':
      try:runtime=audit.csv_rows(folder/'wave_runtime.csv')
      except OSError:runtime=[]
      if len(runtime)>=10:
       tail=runtime[-10:];pv=[float(x['actual_period_s']) for x in tail]
       if any(not math.isfinite(float(x['evaluated_height_m'])) or abs(float(x['evaluated_height_m'])-s['height_m'])>1e-9 for x in tail) or any(not math.isfinite(x) or x<=0 for x in pv):reason='Invalid wave runtime';(folder/'STOP').touch()
       elif max(pv)-min(pv)>1e-6*statistics.mean(pv):reason='Wave period not stable';(folder/'STOP').touch()
       else:
        if period is None:period=statistics.mean(pv);m.write(folder/'frozen_period.json',dict(period_s=period,activation_time_s=activation_t,samples=10,height_m=s['height_m']))
        if abs(statistics.mean(pv)-period)>1e-6*period:reason='Wave period changed after freezing';(folder/'STOP').touch()
        if not arrival_result or not arrival_result.get('established'):
         arrival_result=arrival.assess(folder,activation_t,period,s['height_m'],s['wavelength_m'],s['xmin_m']);m.write(folder/'arrival_assessment.json',arrival_result)
        if arrival_result.get('established'):
         screen=cycles.evaluate([Path(x) for x in source.get('history_files',[])]+[folder/'history.csv'],period,min_cycles=4,max_cycles=20,analysis_origin_s=arrival_result['analysis_origin_s'])
         screen.update(case=folder.name,updated_at=m.stamp());m.write(folder/'cycle_assessment.json',screen);m.write(R/'wave_cycle_repeatability_current.json',screen)
         if screen.get('stop_for_repeatability'):reason='repeatability_screen_pass';decision=screen;(folder/'STOP').touch()
        if t>=activation_t+20*period and reason is None:reason='20_period_cap_review_required';decision=arrival_result or {}; (folder/'STOP').touch()
    time.sleep(2)
   rc=proc.wait();th.join(10)
  done=m.read(folder/'completed.json');preserved=e.digest(psrc)==source['sha256'] and e.digest(folder/'input.sim')==source['sha256']
  if mode=='wave_setup':
   ok=rc==0 and preserved and m.read(folder/'prepared_wave_audit.json').get('flow_steps')==0 and (folder/'prepared_wave.sim').is_file()
   m.write(folder/'controller_result.json',dict(returncode=rc,source_unchanged=preserved,prepared=ok,mode=mode))
   if not ok:raise Halt('Wave definition preparation failed; inspect preserved attempt')
   return dict(status='prepared_wave_definition',directory=str(folder),file=str(folder/'prepared_wave.sim'),time_s=t0,flow_steps=0)
  if reason is None and (folder/'STOP').exists():reason='User stop'
  if rc!=0 or not preserved or done.get('status') not in ('stopped_by_marker','target_reached','wall_budget') or (folder/'macro_error.txt').exists():raise Halt('Solver/error/physical guard; diagnostic fields preserved')
  native=audit.native_audit(folder,done.get('steps',0))
  result=dict(status=reason or 'time_cap_without_convergence',returncode=rc,source_unchanged=preserved,completed=done,decision=decision,native=native,directory=str(folder),file=str(folder/'final.sim'),elapsed_s=time.monotonic()-started)
  m.write(folder/'controller_result.json',result)
  if not native.get('pass'):raise Halt('Native report sampling audit failed; review preserved results')
  if reason in ('calm_settled','repeatability_screen_pass'):
   cp=m.read(folder/'latest_checkpoint.json');last=audit.csv_rows(folder/'history.csv')[-1];saved_time=audit.number(done.get('time_s'))
   if saved_time is None or cp.get('kind')!='final' or cp.get('completed_save') is not True or cp.get('guard_checked') is not True or Path(cp.get('file','missing')).resolve()!=(folder/'final.sim').resolve() or audit.number(cp.get('time_s')) is None or abs(cp['time_s']-saved_time)>1e-8 or audit.number(last.get('time_s')) is None or abs(float(last['time_s'])-saved_time)>1e-8 or cp.get('dt_s')!=dt:raise Halt('Accepted-screen final save does not match its guarded sample')
  if reason=='calm_settled':
   checkpoint=folder/'C01_settled.sim';shutil.copy2(folder/'final.sim',checkpoint);sha=e.digest(checkpoint)
   manifest=dict(status='calm_force_settled',file=str(checkpoint),sha256=sha,physical_time_s=done['time_s'],cells=source['cells'],domain_x_m=[s['xmin_m'],s['xmax_m']],domain_z_m=[-22,8],depth_m=24,span_m=.02,source_unchanged=True,source=str(psrc),source_sha256=source['sha256'],settling=dict(decision,passed=True),dt_s=dt,inner=10,order='SECOND_ORDER',mesh_id=s['mesh_id'],mesh_sha256=s['mesh_sha256'],domain_key=m.domain_key(s),pressure_AMG_tolerance=.01,wave_active=False,mesh=source.get('mesh'),native=native)
   m.write(folder/'settled_checkpoint.json',manifest);m.write(folder/'latest_checkpoint.json',dict(cp,file=str(checkpoint),kind='settled_calm',time_s=done['time_s'],completed_save=True))
   (D/'calm').mkdir(parents=True,exist_ok=True);m.write(D/'calm'/f"{m.domain_key(s)}.json",dict(manifest=str(folder/'settled_checkpoint.json')))
   return dict(manifest,manifest=str(folder/'settled_checkpoint.json'))
  if reason in ('User paused queue','User stop','Wall-time limit') or done.get('status')=='wall_budget':
   if not (folder/'final.sim').is_file():raise Halt('No completed saved state for continuation')
   last=audit.csv_rows(folder/'history.csv')[-1]
   if any(audit.number(last.get(k)) is None for k in ('time_s','max_speed_m_s','alpha_min','alpha_max')):raise Halt('Cannot verify saved fields for continuation')
   cp=m.read(folder/'latest_checkpoint.json');saved_time=audit.number(done.get('time_s'))
   if saved_time is None or saved_time<=0 or cp.get('kind')!='final' or cp.get('completed_save') is not True or cp.get('guard_checked') is not True or Path(cp.get('file','missing')).resolve()!=(folder/'final.sim').resolve() or audit.number(cp.get('time_s')) is None or abs(cp['time_s']-saved_time)>1e-8 or abs(float(last['time_s'])-saved_time)>1e-8 or cp.get('dt_s')!=dt:raise Halt('Final checkpoint guard/time/profile metadata does not match the saved continuation')
   for field in ('max_speed_m_s','alpha_min','alpha_max'):
    if audit.number(cp.get(field)) is None or abs(float(cp[field])-float(last[field]))>1e-8*max(1,abs(float(last[field]))):raise Halt('Final checkpoint fields differ from the recorded guard sample')
   if float(last['max_speed_m_s'])>50 or float(last['alpha_min'])< -1e-8 or float(last['alpha_max'])>1+1e-8:raise Halt('Guard-failed fields cannot continue')
   manifest=dict(status='safe_saved_continuation',mode=mode,file=str(folder/'final.sim'),sha256=e.digest(folder/'final.sim'),physical_time_s=done['time_s'],cells=source['cells'],mesh=source.get('mesh'),mesh_id=s['mesh_id'],mesh_sha256=s['mesh_sha256'],domain_key=m.domain_key(s),dt_s=dt,inner=10,order='SECOND_ORDER',source_unchanged=True,physical_guard_failed=False,activation_time_s=activation_t,period_s=period,arrival_assessment=arrival_result,history_files=source.get('history_files',[])+[str(folder/'history.csv')],history_sha256={str(x):e.digest(Path(x)) for x in source.get('history_files',[])+[str(folder/'history.csv')]},native=native,saved_at=m.stamp())
   m.write(folder/'resume_manifest.json',manifest);return dict(result,status='paused',resume_manifest=str(folder/'resume_manifest.json'))
  if reason!='repeatability_screen_pass':raise Halt(reason or 'No completed repeatability screen')
  return result
 except BaseException as ex:
  if proc is not None and proc.poll() is None:
   (folder/'STOP').touch()
   try:proc.wait(timeout=600)
   except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  if folder.exists():m.write(folder/'local_error.json',dict(error=e.redact(str(ex)),at=m.stamp()))
  raise
 finally:
  live=proc is not None and proc.poll() is None
  if not live:
   state=m.read(R/'wave_foil_run_state.json')
   if state.get('case')==folder.name:
    state.update(computation_active=False,status='saved_pending_review',updated_at=m.stamp(),progress=m.read(folder/'completed.json') or state.get('progress',{}));m.write(R/'wave_foil_run_state.json',state)
   release(lock,token)
def process_job(j):
 ensure_not_cancelled(j)
 s=j['spec'];status(j,'Waiting for the current owned calculation to finish',status='waiting')
 while not safe_ready():
  ensure_not_cancelled(j)
  if pause():raise Halt('Queue paused')
  time.sleep(3)
 ensure_not_cancelled(j)
 if pause():raise Halt('Queue paused')
 resume=j.pop('resume_source',None)
 if resume:
  result=execute_solver(j,resume['mode'],resume)
  if result.get('status')=='paused' or resume['mode']=='wave':return result
  calm=result
 else:calm=m.registered_calm(s,verify=True)
 if not calm:
  prepared=domain.existing(s)
  if prepared is None or s['action']=='prepare':
   ensure_not_cancelled(j)
   prepared=domain.prepare(s,j['id'],lambda text,path:status(j,text,status='preparing',preparation_directory=path))
  if s['action']=='prepare':
   return dict(status='prepared_calm_input',file=prepared['path'],time_s=0,flow_steps=0,message='New geometry is prepared; Run will settle its own C01 before waves')
  ensure_not_cancelled(j)
  if pause():raise Halt('Queue paused after domain preparation; no calm solver started')
  calm=execute_solver(j,'calm',prepared)
  if calm.get('status')=='paused':return calm
 if pause():raise Halt('Queue paused after C01 save')
 return execute_solver(j,'wave_setup' if s['action']=='prepare' else 'wave',calm)
def main():
 if sys.argv[1:]!=['--run']:raise SystemExit('Use --run; requests come from the local control dashboard')
 if pause() or not m.readiness()['ready']:raise Halt('Campaign hold/pause or recipe checks prevent flow launch')
 D.mkdir(exist_ok=True);token=uuid.uuid4().hex;lock=D/'worker.lock';own_lock(lock,token)
 k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
 if not k.SetProcessAffinityMask(k.GetCurrentProcess(),3):release(lock,token);raise Halt('Cannot set owned process affinity')
 k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.SetPriorityClass(k.GetCurrentProcess(),0x20)
 k.SetThreadExecutionState(0x80000001)
 try:
  if any(j.get('status') in ('running','preparing') for j in m.jobs()):raise Halt('Unreconciled previous job; no attempt is restarted')
  while not pause():
   pending=[j for j in m.jobs() if j.get('status') in ('queued','waiting')]
   if not pending:break
   j=pending[0]
   try:
    result=process_job(j);j['results'].append(result)
    if result.get('status')=='paused':
     status(j,'Stopped normally and saved. Continue creates a new attempt from this checkpoint.',status='paused',resume_manifest=result['resume_manifest']);(D/'PAUSE').touch();break
    status(j,'Saved result ready',status='completed')
   except Cancelled:
    j=m.read(D/'jobs'/j['id']/'job.json');status(j,'Cancelled; no next phase launched',status='cancelled')
   except BaseException as ex:stop_report(j,e.redact(str(ex)));break
   finally:
    try:subprocess.run([sys.executable,str(R/'build_local_control_report.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:pass
  m.write(D/'state.json',dict(status='paused' if pause() else 'idle',updated_at=m.stamp(),message='Queue paused for user/review' if pause() else 'Queued work complete'))
 finally:k.SetThreadExecutionState(0x80000000);release(lock,token)
if __name__=='__main__':main()
