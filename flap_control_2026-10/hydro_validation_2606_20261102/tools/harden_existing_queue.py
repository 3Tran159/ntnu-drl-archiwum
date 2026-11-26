from pathlib import Path
import json,datetime,shutil,ast
H=Path(__file__).resolve().parents[1]
assert not (H/'audit/night_queue.lock').exists()
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');b=H/'audit'/('before_queue_hardening_'+stamp);b.mkdir()
p=H/'tools/night_queue.py';shutil.copy2(p,b/p.name);s=p.read_text()
def rep(a,z):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,z)
rep("   if cfg.get('controller_exit_requested') and not st.get('active'):event('controller_graceful_exit');break", "   if cfg.get('controller_exit_requested') and not st.get('active'):\n    st['queue_state']='CONTROLLER_STOPPED';publish(st,cfg,{},resources());event('controller_graceful_exit');break")
rep(" if old.get('pid') in alive:raise RuntimeError('Queue already active; adopt its state, do not start duplicate')", " if old.get('pid') in alive and (not old.get('born') or any(p['pid']==old['pid'] and p['born']==old['born'] for p in plist)):raise RuntimeError('Queue already active; adopt its state, do not start duplicate')")
rep("json.dump(dict(pid=os.getpid(),at=now()),f)","json.dump(dict(pid=os.getpid(),at=now(),born=next((p['born'] for p in plist if p['pid']==os.getpid()),None)),f)")
rep(" from benchmark_telemetry import start_telemetry\n start_telemetry(H)"," try:\n  from benchmark_telemetry import start_telemetry\n  start_telemetry(H)\n except Exception:event('optional_telemetry_unavailable',error=traceback.format_exc())")
rep("   validate(cfg);plist=processes();rs=resources()", "   validate(cfg);plist=processes();rs=resources()\n   from queue_safety import recover_launch\n   recovered=recover_launch(H,st,cfg,plist,output_path)\n   if recovered:event(recovered)")
rep("pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs']]", "pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]")
rep("      st['queue_state']='LAUNCHING';publish(st,cfg,{},rs)", "      from queue_safety import launch_integrity\n      try:launch_integrity(H,j)\n      except Exception as integrity_error:\n       st['failure_hold']=j['id'];st['jobs'][j['id']]=dict(state='input_integrity_failed',reason=str(integrity_error));publish(st,cfg,{},rs);event('input_integrity_failed',job=j['id'],reason=str(integrity_error));continue\n      st['launch_intent']=dict(id=j['id'],at=now());st['queue_state']='LAUNCHING';publish(st,cfg,{},rs)")
rep("rec.update(id=j['id'],output=str(output_path(rec)),initial_time_s=j.get('initial_time_s',0),state='active');st['active']=rec;st['next_job']=None;", "rec.update(id=j['id'],output=str(output_path(rec)),initial_time_s=j.get('initial_time_s',0),state='active');st['active']=rec;st.pop('launch_intent',None);st['next_job']=None;")
rep("       st['failure_hold']=j['id'];st['jobs'][j['id']]=dict(state='launch_failed',at=now());", "       st.pop('launch_intent',None);st['failure_hold']=j['id'];st['jobs'][j['id']]=dict(state='launch_failed',at=now());")
rep("    runtime=active_job.get('runtime_guards',{})", "    from queue_safety import job_watchdog\n    stalled=job_watchdog(st['active'],metrics,active_job)\n    if stalled:\n     marker=H.parent/'STOP_OWNED_CFD.json'\n     if not marker.exists():atomic(marker,dict(source='night_queue',reason=stalled,at=now(),target_job=st['active']['id']));event('watchdog_graceful_stop_requested',reason=stalled,job=st['active']['id'])\n     st['queue_state']='WATCHDOG_HOLD';cfg['accept_new_jobs']=False;atomic(CFG,cfg)\n    runtime=active_job.get('runtime_guards',{})")
rep("  st['jobs'][rec['id']]=rec;st['active']=None;st['last_metrics']=metrics;st['owned_processes']={}","  if success and not rec['macro'].startswith('Inspect') and not metrics.get('checkpoint_integrity',{}).get('native_save_complete'):\n   success=False;rec['state']='failed';rec['completion_error']='No verified native complete checkpoint'\n  from queue_safety import automatic_job_report\n  automatic_job_report(H,rec)\n  st['jobs'][rec['id']]=rec;st['active']=None;st['last_metrics']=metrics;st['owned_processes']={}")
rep("  if not success:st['failure_hold']=rec['id']", "  if not success:st['failure_hold']=rec['id']\n  st['queue_state']='HOLD_FAILED_JOB' if not success else 'HOLD_SCIENTIFIC_REVIEW'")
ast.parse(s);p.write_text(s,encoding='utf8')
cfg=json.loads((H/'NIGHT_QUEUE.json').read_text());st=json.loads((H/'NIGHT_QUEUE_STATE.json').read_text())
assert st.get('active') is None and st['failure_hold']=='plus2_benchmark_8cpu_20261103'
for j in cfg['jobs']:
 if j['id'] in ['plus2_benchmark_12cpu_20261103','plus2_benchmark_16cpu_20261103']:
  j.update(approved=False,disabled=True);st['jobs'][j['id']]=dict(state='blocked_not_run',reason='First+2step failed pressure gate; user requests no later variants',id=j['id'])
cfg.update(accept_new_jobs=False,controller_exit_requested=False)
(H/'NIGHT_QUEUE.json').write_text(json.dumps(cfg,indent=2),encoding='utf8');(H/'NIGHT_QUEUE_STATE.json').write_text(json.dumps(st,indent=2),encoding='utf8')
review=json.loads((H/'WORK_CURRENT_REVIEW.json').read_text());review.update(current_job_kind='plus2_hold',status='FAIL_PLUS2_SCIENTIFIC_HOLD',last_decision='First+2step failed pressure threshold at0.672s. Checkpoint and scientific report secured.12/16MPI tests and all later variants blocked. Existing queue hardening only.',obstacle='Negative absolute pressure at upper flap nose. No validated +2forces; CPU benchmark incomplete.',next='Local queue reliability checks; no CFD launch.',current_run=str(H/'cases/SP_C_split0_overset/plus2_benchmark_20261103_091101'));(H/'WORK_CURRENT_REVIEW.json').write_text(json.dumps(review,indent=2),encoding='utf8')
from queue_safety import automatic_job_report
automatic_job_report(H,st['jobs']['plus2_benchmark_8cpu_20261103'])
print(str(b))
