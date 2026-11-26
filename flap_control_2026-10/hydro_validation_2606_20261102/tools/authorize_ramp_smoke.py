from pathlib import Path
import json,datetime,hashlib,shutil,ast
H=Path(__file__).resolve().parents[1];R=H.parent
E='RAMP_C0_PLUS2_S5_20261103';J=E+'_SMOKE'
cfg=json.loads((H/'NIGHT_QUEUE.json').read_text());st=json.loads((H/'NIGHT_QUEUE_STATE.json').read_text());assert st.get('active') is None and not (H/'audit/night_queue.lock').exists()
b=H/'audit'/('before_ramp_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));b.mkdir()
def change(n,fn):
 p=H/'tools'/n;shutil.copy2(p,b/n);s=fn(p.read_text());ast.parse(s);p.write_text(s,encoding='utf8')
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def queue(s):
 s=rep(s,'def now():',"ALLOWED.update(['RampPlus2Smoke.java','RampPlus2Run.java'])\nfrom ramp_authorization import blocks as failure_blocks_job\ndef now():")
 s=rep(s,"  elif j.get('kind')=='benchmark':","  elif j.get('kind')=='ramp':\n   assert j['macro'] in ['RampPlus2Smoke.java','RampPlus2Run.java'] and j.get('cpu_processes')==8 and j.get('angle_deg')==2\n   assert j.get('experiment_id')=='RAMP_C0_PLUS2_S5_20261103'\n  elif j.get('kind')=='benchmark':")
 s=rep(s,'def output_path(receipt):',"def output_path(receipt):\n if receipt['macro'] in ['RampPlus2Smoke.java','RampPlus2Run.java']:return H/'cases/SP_C_split0_overset'/('ramp_plus2_'+receipt['run_id'])")
 s=rep(s,"['benchmark_complete','static_pose_prepared'", "['ramp_smoke_passed','ramp_stable_candidate','ramp_paused','benchmark_complete','static_pose_prepared'")
 s=rep(s,"['checkpoint.sim','error_checkpoint.sim','motion_verified.sim'", "['checkpoint.sim','paused_checkpoint.sim','error_checkpoint.sim','motion_verified.sim'")
 s=rep(s,"    elif st.get('failure_hold') and not cfg.get('release_failure_hold',{}).get(st['failure_hold']):st['queue_state']='HOLD_FAILED_JOB'", "    elif failure_blocks_job(st,cfg,pending[0] if pending else None):st['queue_state']='HOLD_FAILED_JOB'")
 s=s.replace("rec.update(id=j['id'],output=", "rec.update(id=j['id'],experiment_id=j.get('experiment_id'),output=")
 s=rep(s," atomic(H/'NIGHT_STATUS.json',base)"," if review.get('current_job_kind')=='ramp':\n  base['current_case_label']='C0 -> smoothstep+2deg';base['mesh_cells']=333939;base['max_cpu_processes']=8;base['flow_frozen']=False\n  if not active and view['metrics'].get('physical_time_s') is not None:base['physical_time_s']=view['metrics']['physical_time_s']\n  if view['metrics'].get('last_output_sim'):base['last_checkpoint']=view['metrics']['last_output_sim']\n  base['last_solved_case']='Smooth ramp diagnostic';base['operation']=base['solver_state'];view['operation']=view['solver_state']=base['solver_state'];atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
 return s
change('night_queue.py',queue)
change('night_native.py',lambda s:rep(s,"name=sys.argv[1];assert name in allowed", "allowed['RampPlus2Smoke.java']=8\nallowed['RampPlus2Run.java']=8\nname=sys.argv[1];assert name in allowed"))
source=H/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'
with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest=='c8b2396f2d087112d06045b06a6c62e93c4003eafde969aa8c8d0ca8120afc10'
macro=H/'macros/RampPlus2Smoke.java'
approval=dict(experiment_id=E,approved_by_user=True,approval_source='User message: OSTATNI PRIORYTET WORK — PRZYGOTOWANIE AUTONOMICZNEJ RAMPY,03.11.2026',previous_case_remains_failed=True,previous_blocked_job='plus2_benchmark_8cpu_20261103',approved_job_ids=[J],scope='5step flow smoke now; bounded autonomous ramp/hold only after positive review',source=str(source),source_sha256=digest,dt=.002,cpu=8,gpu=False,delta_target_deg=2,ramp_duration_s=.2)
ap=H/'audit/RAMP_PLUS2_EXPLICIT_APPROVAL_20261103.json';ap.write_text(json.dumps(approval,indent=2),encoding='utf8')
cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=approval['previous_blocked_job'],evidence=str(ap))
job=dict(id=J,kind='ramp',experiment_id=E,approved=True,macro=macro.name,macro_sha256=hashlib.sha256(macro.read_bytes()).hexdigest(),input=str(source),input_sha256=digest,initial_time_s=.65,cpu_processes=8,angle_deg=2,progress_timeout_s=900,maximum_runtime_s=1800)
assert J not in st['jobs'] and not any(j['id']==J for j in cfg['jobs']);cfg['jobs'].append(job);cfg.update(accept_new_jobs=True,controller_exit_requested=False)
marker=R/'STOP_OWNED_CFD.json';m=json.loads(marker.read_text());assert m.get('source')=='cfd_control' and m.get('reason')=='manual_stop';marker.replace(b/marker.name)
(H/'NIGHT_QUEUE.json').write_text(json.dumps(cfg,indent=2),encoding='utf8')
review=json.loads((H/'WORK_CURRENT_REVIEW.json').read_text());review.update(current_job_kind='ramp',last_decision='Explicitly approved separate C0 smoothstep ramp. Old stepped+2 remains FAIL. Five active URANS steps only; full continuation requires smoke review.',obstacle='Ramp smoke pending; no full-ramp validation claimed.',next='If smoke passes,prepare local continuation without launching it.');(H/'WORK_CURRENT_REVIEW.json').write_text(json.dumps(review,indent=2),encoding='utf8')
with (H/'NIGHT_DECISIONS.jsonl').open('a') as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),kind='explicit_separate_experiment_authorization',evidence=str(ap),job=job,old_failure_released=False))+'\n')
print(json.dumps(job,indent=2))
