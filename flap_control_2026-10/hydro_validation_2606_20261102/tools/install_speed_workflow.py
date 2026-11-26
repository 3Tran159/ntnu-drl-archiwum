from pathlib import Path
import json,hashlib,datetime,shutil
H=Path(__file__).resolve().parents[1];R=H.parent;T=H/'tools';E='SPEED_SWEEP_PLUS2_20261103'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):p.with_suffix(p.suffix+'.tmp').write_text(json.dumps(v,indent=2),encoding='utf8');p.with_suffix(p.suffix+'.tmp').replace(p)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
st=read(H/'NIGHT_QUEUE_STATE.json');cfg=read(H/'NIGHT_QUEUE.json')
assert st.get('active') is None and st['queue_state']=='CONTROLLER_STOPPED'
assert not (H/'audit/night_queue.lock').exists()
assert st['failure_hold']=='RAMP_C0_PLUS2_S5_20261103_RUN'
backup=H/'audit'/('before_speed_workflow_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for rel in ['tools/night_queue.py','tools/night_native.py','tools/night_dashboard.py','tools/ramp_authorization.py','tools/cfd_control.py','NIGHT_QUEUE.json','WORK_CURRENT_REVIEW.json']:
 shutil.copy2(H/rel,backup/Path(rel).name)
def patch(file,a,b):
 p=T/file;s=p.read_text();assert s.count(a)==1,(file,a,s.count(a));p.write_text(s.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"if not job or job.get('experiment_id')!=EXPERIMENT:return True", "if not job or job.get('experiment_id') not in [EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103']:return True\n experiment=job['experiment_id']")
patch('ramp_authorization.py',".get(EXPERIMENT,{})", ".get(experiment,{})")
patch('ramp_authorization.py',"e.get('experiment_id')==EXPERIMENT", "e.get('experiment_id')==experiment")
patch('night_native.py',"name=sys.argv[1];", "allowed['SpeedSweepPlus2Smoke.java']=8\nallowed['SpeedSweepPlus2Run.java']=8\nname=sys.argv[1];")
patch('night_queue.py',"from ramp_authorization import blocks", "ALLOWED.update(['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java'])\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='ramp':", "  elif j.get('kind')=='speed_sweep':\n   assert j['macro'] in ['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java'] and j.get('cpu_processes')==8 and j.get('angle_deg')==2\n   assert j.get('experiment_id')=='SPEED_SWEEP_PLUS2_20261103'\n  elif j.get('kind')=='ramp':")
patch('night_queue.py',"def output_path(receipt):", "def output_path(receipt):\n if receipt['macro'] in ['SpeedSweepPlus2Smoke.java','SpeedSweepPlus2Run.java']:return H/'cases/SP_C_split0_overset'/('speed_plus2_'+receipt['run_id'])")
patch('night_queue.py',"['ramp_smoke_passed','ramp_stable_candidate'", "['speed_smoke_passed','speed_sweep_complete','speed_paused','ramp_smoke_passed','ramp_stable_candidate'")
patch('night_queue.py',"for k in ['flap_angle_deg'", "for k in ['U_m_s','target_U_m_s','stage','Re','qS_N','flap_angle_deg'")
patch('night_queue.py'," atomic(H/'NIGHT_STATUS.json',base)", " if review.get('current_job_kind')=='speed_sweep':\n  from speed_dashboard import publish_speed\n  publish_speed(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
patch('night_dashboard.py'," if review0.get('current_job_kind')=='ramp':", " if review0.get('current_job_kind')=='speed_sweep':\n  from speed_dashboard import render_speed\n  return render_speed(h,view,base,review0)\n if review0.get('current_job_kind')=='ramp':")
patch('cfd_control.py',"selected.get('experiment_id')=='RAMP_C0_PLUS2_S5_20261103'", "selected.get('experiment_id') in ['RAMP_C0_PLUS2_S5_20261103','SPEED_SWEEP_PLUS2_20261103']")
source=H/'cases/SP_C_split0_overset/static_plus2_prepared_20261103_085250/SP_C_plus2_prepared_NOT_SOLVED_2606.sim'
assert sha(source)=='4f5fd71acc76a75f21fbacdaa8d6e2e0c3b4145d34fd3480b0a19429fbeba22a'
macro=H/'macros/SpeedSweepPlus2Smoke.java';jid=E+'_SMOKE'
job=dict(id=jid,experiment_id=E,kind='speed_sweep',approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(source),input_sha256=sha(source),initial_time_s=0.0,cpu_processes=8,angle_deg=2,progress_timeout_s=900,maximum_runtime_s=1800)
assert not any(j['id']==jid for j in cfg['jobs'])
ap=H/'audit/SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json'
approval=dict(approved_by_user=True,experiment_id=E,previous_case_remains_failed=True,previous_blocked_job=st['failure_hold'],approved_job_ids=[jid],source='User request NTNU CFD AUTONOMOUS VELOCITY SWEEP FIXED FLAP +2, 2026-11-03',scope='Fixed+2 at 10/12/14/16/18m/s, serial gated stages,8CPU,noGPU; full run prepared only after short native smoke. No other angles/waves.',pabs_threshold_Pa=12339.214766776897,source_checkpoint=str(source),source_sha256=job['input_sha256'],new_initialization='Fresh10m/s fields/history in independent working state; geometry/mesh/SST/Overset unchanged; source never overwritten',full_run_macro_sha256=sha(H/'macros/SpeedSweepPlus2Run.java'))
write(ap,approval)
cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap))
cfg['jobs'].append(job);cfg.update(accept_new_jobs=True,controller_exit_requested=False);write(H/'NIGHT_QUEUE.json',cfg)
(H/'audit/SPEED_PLUS2_RUNTIME.properties').write_text(f'input={source.as_posix()}\ntime_s=0.67\niteration=11570\nstage=0\nstage_start_s=0\n',encoding='utf8')
review=read(H/'WORK_CURRENT_REVIEW.json');review.update(at=datetime.datetime.now().astimezone().isoformat(),status='SPEED_SWEEP_SMOKE_PENDING',current_job_kind='speed_sweep',current_case_label='Fixed +2deg velocity sweep',last_decision='Independent fixed+2/10m/s fresh initialization. Ramp FAIL preserved at t0.806,pmin12333.273Pa. Native five-step smoke only authorized now.',obstacle='Native fresh initialization/startup untested',next='Review short smoke; prepare full gated sweep without executing it',parameters={**review.get('parameters',{}),'CPU_max':8,'U':10,'delta':2});write(H/'WORK_CURRENT_REVIEW.json',review)
print(json.dumps(dict(backup=str(backup),smoke=job,old_failure=st['failure_hold']),indent=2))
