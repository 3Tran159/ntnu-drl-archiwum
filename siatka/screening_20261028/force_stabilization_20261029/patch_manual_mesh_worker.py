from pathlib import Path
import datetime,shutil
r=Path('F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');p=r/'local_control_worker.py'
s=p.read_text(encoding='utf8');shutil.copy2(p,r/('local_control_worker_before_manual_mesh_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.py'))
def rep(a,b):
 global s
 assert s.count(a)==1,(a[:120],s.count(a))
 s=s.replace(a,b)
rep('def calm_screen(path):','def calm_screen(path,dt=.001):')
rep("if bad or len(rows)<400:","if bad or len(rows)<round(.4/dt):")
rep(">.00101 for a,b",">dt*1.01 for a,b")
rep("if min(len(previous),len(current))<199:","if min(len(previous),len(current))<round(.2/dt)-1:")
rep("reason='At least199 samples required in each0.2s window'","reason='Insufficient time-step samples in a 0.2s window'")
rep("def pause():return (D/'PAUSE').exists() or (R/'STOP_ALL').exists()","def pause():return (D/'PAUSE').exists() or (R/'STOP_ALL').exists() or m.hold().get('active',False)")
rep("s=j['spec'];t0=source.get('physical_time_s',0);token=uuid.uuid4().hex","s=j['spec'];t0=source.get('physical_time_s',0);token=uuid.uuid4().hex;dt=s['dt_s'];resuming=source.get('status')=='safe_saved_continuation';activation_t=source.get('activation_time_s',t0)\n selected=m.mesh_profile(s['mesh_id'])\n if selected['file_sha256']!=s['mesh_sha256']:raise Halt('Inspected mesh identity changed; create a new job')")
rep("if mode!='calm' and (source.get('status')!='calm_force_settled' or not source.get('source_unchanged')):raise Halt('A settled matching C01 is required')","if mode!='calm' and (source.get('status') not in ('calm_force_settled','safe_saved_continuation') or not source.get('source_unchanged')):raise Halt('A matching settled C01 or verified continuation is required')\n if resuming and (source.get('physical_guard_failed') is not False or source.get('mode')!=mode or source.get('domain_key')!=m.domain_key(s) or source.get('dt_s')!=dt):raise Halt('Continuation profile or guard mismatch')")
rep("source_calm_settled=mode!='calm'","source_calm_settled=mode!='calm' and not resuming")
rep("remaining=6-t0 if mode=='calm' else 40\n  steps=round((remaining-(.02 if t0==0 else 0))/.001)","remaining=6-t0 if mode=='calm' else 40\n  startup_duration=40*min(dt,.0005) if t0==0 else 0\n  steps=round((remaining-startup_duration)/dt)")
rep("NTNU_WAVE_DT='.001'","NTNU_WAVE_DT=str(dt)")
rep("NTNU_ZONE=str(s['zone_m']))","NTNU_ZONE=str(s['zone_m']),NTNU_CHECKPOINT_INTERVAL_S=str(s.get('checkpoint_interval_s',.05)),NTNU_RESUME_WAVE=str(resuming and mode=='wave').lower(),NTNU_WAVE_ACTIVATION_TIME=str(activation_t))")
rep("last_t=t0;last_change=time.monotonic();last_eval=0;period=None;arrival_result=None;decision={}","last_t=t0;last_change=time.monotonic();last_eval=0;period=source.get('period_s') if resuming else None;arrival_result=source.get('arrival_assessment') if resuming else None;decision={}\n   if period is not None:m.write(folder/'frozen_period.json',dict(period_s=period,activation_time_s=activation_t,inherited=True))")
rep("source_time_s=t0,activation=activation","source_time_s=t0,dt_s=dt,mesh_id=s['mesh_id'],activation=activation")
rep("calm_screen(folder/'history.csv')","calm_screen(folder/'history.csv',dt)")
rep("activation_time_s=t0,samples=10","activation_time_s=activation_t,samples=10")
rep("arrival.assess(folder,t0,period","arrival.assess(folder,activation_t,period")
rep("cycles.evaluate([folder/'history.csv'],period","cycles.evaluate([Path(x) for x in source.get('history_files',[])]+[folder/'history.csv'],period")
rep("if t>=t0+20*period","if t>=activation_t+20*period")
rep("if reason!='repeatability_screen_pass':raise Halt(reason or 'No completed repeatability screen')",
"""if reason in ('User paused queue','User stop','Wall-time limit') or done.get('status')=='wall_budget':
   if not (folder/'final.sim').is_file():raise Halt('No completed saved state for continuation')
   last=audit.csv_rows(folder/'history.csv')[-1]
   if any(audit.number(last.get(k)) is None for k in ('time_s','max_speed_m_s','alpha_min','alpha_max')):raise Halt('Cannot verify saved fields for continuation')
   if float(last['max_speed_m_s'])>50 or float(last['alpha_min'])< -1e-8 or float(last['alpha_max'])>1+1e-8:raise Halt('Guard-failed fields cannot continue')
   manifest=dict(status='safe_saved_continuation',mode=mode,file=str(folder/'final.sim'),sha256=e.digest(folder/'final.sim'),physical_time_s=done['time_s'],cells=source['cells'],mesh=source.get('mesh'),mesh_id=s['mesh_id'],mesh_sha256=s['mesh_sha256'],domain_key=m.domain_key(s),dt_s=dt,inner=10,order='SECOND_ORDER',source_unchanged=True,physical_guard_failed=False,activation_time_s=activation_t,period_s=period,arrival_assessment=arrival_result,history_files=source.get('history_files',[])+[str(folder/'history.csv')],native=native,saved_at=m.stamp())
   m.write(folder/'resume_manifest.json',manifest);return dict(result,status='paused',resume_manifest=str(folder/'resume_manifest.json'))
  if reason!='repeatability_screen_pass':raise Halt(reason or 'No completed repeatability screen')""")
# Previous branch would archive pause before we can offer continuation? It occurs only after calm-settled branch, fine.
rep("dt_s=.001,inner=10,order='SECOND_ORDER'","dt_s=dt,inner=10,order='SECOND_ORDER',mesh_id=s['mesh_id'],mesh_sha256=s['mesh_sha256'],domain_key=m.domain_key(s)")
rep("calm=m.registered_calm(s,verify=True)","resume=j.pop('resume_source',None)\n if resume:\n  result=execute_solver(j,resume['mode'],resume)\n  if result.get('status')=='paused' or resume['mode']=='wave':return result\n  calm=result\n else:calm=m.registered_calm(s,verify=True)")
rep("calm=execute_solver(j,'calm',prepared)","calm=execute_solver(j,'calm',prepared)\n  if calm.get('status')=='paused':return calm")
rep("result=process_job(j);j['results'].append(result);status(j,'Saved result ready',status='completed')","result=process_job(j);j['results'].append(result)\n    if result.get('status')=='paused':\n     status(j,'Stopped normally and saved. Continue creates a new attempt from this checkpoint.',status='paused',resume_manifest=result['resume_manifest']);(D/'PAUSE').touch();break\n    status(j,'Saved result ready',status='completed')")
# Check readiness once at worker entry, not merely at dashboard request time.
rep("D.mkdir(exist_ok=True);token=uuid.uuid4().hex;lock=D/'worker.lock';own_lock(lock,token)","if pause() or not m.readiness()['ready']:raise Halt('Campaign hold/pause or recipe checks prevent flow launch')\n D.mkdir(exist_ok=True);token=uuid.uuid4().hex;lock=D/'worker.lock';own_lock(lock,token)")
compile(s,str(p),'exec');p.write_text(s,encoding='utf8');print('Worker updated; no processes launched')
