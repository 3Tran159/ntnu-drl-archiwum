from pathlib import Path
import py_compile,shutil,datetime
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py'
shutil.copy2(p,h/'audit'/('night_queue_before_v2_'+datetime.datetime.now().strftime('%H%M%S')+'.py'))
s=p.read_text(encoding='utf8')
s=s.replace("Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(starccm\\+|star-ccm\\+|starccmw|mpiexec|smpd|python)\\.exe$'} | ForEach-Object", "Get-CimInstance Win32_Process | ForEach-Object")
s=s.replace("if old.get('pid') in alive:raise RuntimeError('Queue already active; adopt its state, do not start duplicate')","if old.get('pid') in alive:raise RuntimeError('Queue already active; adopt its state, do not start duplicate')")
s=s.replace("atomic(STATE,st)","""atomic(STATE,st)
 base=read(H/'validation/C0_actual_resume_20261102_221053.json',{})
 active=st.get('active')
 base.update(at=view['at'],local_queue_started=True,queue_pid=os.getpid(),queue_state=view['queue_state'],resources=rs,scientific_gates=cfg['scientific_gates'],active_operation=active['macro'] if active else 'Awaiting scientific decision',active_input=active['input'] if active else None,actual_live_metrics=view['metrics'],dashboard=str(H/'NIGHT_DASHBOARD.html'))
 if active and not active['macro'].startswith('Inspect'):
  moving=view['metrics'].get('physical_time_s',0)>active.get('initial_time_s',0) and bool(view['metrics'].get('owned_active_pids'))
  base['solver_state']='RUNNING' if moving else 'STOPPED'
  if moving and view['metrics'].get('seconds_without_log_write',0)>900 and not view['metrics'].get('saving_or_exporting'):base['solver_state']='STALLED'
  base['physical_time_s']=view['metrics'].get('physical_time_s',active.get('initial_time_s'))
  if view['metrics'].get('last_output_sim'):base['last_checkpoint']=view['metrics']['last_output_sim']
 else:base['solver_state']='STOPPED'
 atomic(H/'NIGHT_STATUS.json',base)""")
s=s.replace("cfg=read(CFG);validate(cfg);plist=processes();rs=resources()","cfg=read(CFG);validate(cfg);plist=processes();rs=resources()\n   if cfg.get('controller_exit_requested'):event('controller_graceful_exit');break")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True);print('v2 ready: complete child tree tracking and live NIGHT_STATUS publishing')
