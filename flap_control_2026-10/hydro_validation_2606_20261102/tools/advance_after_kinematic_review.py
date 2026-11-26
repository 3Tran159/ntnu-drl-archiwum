"""One-time reviewed handover of the existing queue; never starts a solver."""
from pathlib import Path
import ast, datetime, hashlib, json, shutil
H=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text(encoding='utf8'))
def write(p,d):
 t=p.with_suffix(p.suffix+'.handover.tmp');t.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8');t.replace(p)
state=read(H/'NIGHT_QUEUE_STATE.json');cfg=read(H/'NIGHT_QUEUE.json')
assert state.get('active') is None and not (H/'audit/night_queue.lock').exists()
assert cfg['controller_exit_requested'] is True
motion=read(H/'audit/KINEMATIC_POC_REVIEW_20261103.json')
assert motion['accepted'] and motion['steps']==100 and motion['overset_error_cells']==0
assert state['jobs']['kinematic_poc333939_20261103']['state']=='completed'
assert not [j for j in cfg['jobs'] if j['id'] not in state['jobs']]
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup=H/'audit'/('after_motion_queue_handover_'+stamp);backup.mkdir()
for n in ['NIGHT_QUEUE.json','NIGHT_QUEUE_STATE.json','WORK_CURRENT_REVIEW.json']:
 shutil.copy2(H/n,backup/n)
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def change(name,fn):
 p=H/'tools'/name;shutil.copy2(p,backup/name);s=fn(p.read_text(encoding='utf8'));ast.parse(s);p.write_text(s,encoding='utf8')
def queue(s):
 s=rep(s,"ALLOWED.add('KinematicPoc333939.java')","ALLOWED.update(['KinematicPoc333939.java','PrepareStaticPlus2.java'])")
 s=rep(s,"  else:assert j.get('angle_deg',0)==0", "  elif j.get('kind')=='static_preparation':\n   assert j['macro']=='PrepareStaticPlus2.java' and j.get('angle_deg')==2\n   assert cfg['scientific_gates'].get('kinematic_sweep_accepted') is True\n  else:assert j.get('angle_deg',0)==0")
 s=rep(s,'def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='PrepareStaticPlus2.java':return H/'cases/SP_C_split0_overset'/('static_plus2_prepared_'+receipt['run_id'])")
 s=rep(s,"  metrics['saving_or_exporting']='Saving:' in tail[-1000:] or 'Export' in tail[-500:]", "  save_lines=[line for line in tail.splitlines() if 'Saving:' in line]\n  metrics['saving_or_exporting']=bool(save_lines and 'complete (' not in save_lines[-1])")
 s=rep(s,"hp=out/('steady_iterations.csv' if steady else 'history.csv')", "hp=out/('pose_preparation.csv' if rec['macro']=='PrepareStaticPlus2.java' else 'steady_iterations.csv' if steady else 'history.csv')")
 s=rep(s,"    metrics['history_rows']=len(rows)","    if row.get('angle_deg'):metrics['flap_angle_deg']=float(row['angle_deg'])\n    metrics['history_rows']=len(rows)")
 s=rep(s,"     elif candidate.name in ['checkpoint.sim','error_checkpoint.sim'] and rows:saved_time=float(rows[-1]['time_s'])", "     elif candidate.name in ['checkpoint.sim','error_checkpoint.sim','motion_verified.sim','SP_C_plus2_prepared_NOT_SOLVED_2606.sim'] and rows:saved_time=float(rows[-1]['time_s'])")
 s=rep(s,"['kinematic_poc_passed','inspection_complete'", "['static_pose_prepared','kinematic_poc_passed','inspection_complete'")
 s=s.replace("active['macro']!='KinematicPoc333939.java'", "active['macro'] not in ['KinematicPoc333939.java','PrepareStaticPlus2.java']")
 s=s.replace("j['macro']!='KinematicPoc333939.java'", "j['macro'] not in ['KinematicPoc333939.java','PrepareStaticPlus2.java']")
 s=rep(s,"base['flow_frozen']=bool(active and active['macro']=='KinematicPoc333939.java')", "base['flow_frozen']=bool(active and active['macro'] in ['KinematicPoc333939.java','PrepareStaticPlus2.java'])")
 s=rep(s," if active and active['macro'].startswith(('Prepare','Finalize')):\n  base['meshing_or_audit_active']", " if active and active['macro']!='PrepareStaticPlus2.java' and active['macro'].startswith(('Prepare','Finalize')):\n  base['meshing_or_audit_active']")
 s=rep(s," atomic(H/'NIGHT_STATUS.json',base)"," if review.get('current_job_kind') in ['kinematic','static_preparation']:\n  from night_mechanics_dashboard import synchronize\n  synchronize(H,st,view,base,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
 s=rep(s,"st['active']=rec;event('job_launched'", "st['active']=rec;st['next_job']=None;event('job_launched'")
 s=rep(s,"   if cfg.get('controller_exit_requested'):event('controller_graceful_exit');break", "   if cfg.get('controller_exit_requested') and not st.get('active'):event('controller_graceful_exit');break")
 return s
change('night_queue.py',queue)
change('night_native.py',lambda s:rep(s,"allowed['KinematicPoc333939.java']=8", "allowed['KinematicPoc333939.java']=8\nallowed['PrepareStaticPlus2.java']=8"))
def dash(s):
 a=s.index(" if review0.get('current_job_kind')=='kinematic':")
 b=s.index("\n m=view.get('flow_metrics'",a)
 return s[:a]+" if review0.get('current_job_kind') in ['kinematic','static_preparation']:\n  from night_mechanics_dashboard import render_mechanics\n  return render_mechanics(h,view,base,review0)\n"+s[b:]
change('night_dashboard.py',dash)
source=H/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'
with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='c8b2396f2d087112d06045b06a6c62e93c4003eafde969aa8c8d0ca8120afc10'
cp=state['checkpoint_integrity'][motion['checkpoint']]
cp.update(saved_time_s=.85,native_metadata_verified=True,native_info=str(H/'audit/kinematic_checkpoint_info_20261103.txt'))
state['last_metrics']['checkpoint_integrity']=cp
state['next_job']=None
cfg['scientific_gates'].update(kinematic_sweep_accepted=True,kinematic_sweep_evidence=str(H/'audit/KINEMATIC_POC_REVIEW_20261103.json'),reason='B0/C0 native readback, matching numerics, residual and field audit closed for kinematic POC. Full +/-5degree motion passed. Quantitative grid/time and far-field uncertainty remains; no energy or training validation.')
job=dict(id='prepare_static_plus2_20261103',macro='PrepareStaticPlus2.java',input=str(source),approved=True,kind='static_preparation',angle_deg=2,initial_time_s=.65,gate='kinematic_sweep_accepted',approval_evidence=str(H/'audit/KINEMATIC_POC_REVIEW_20261103.json'),hydrodynamic_steps=0)
cfg['jobs'].append(job);cfg.update(controller_exit_requested=False,accept_new_jobs=True)
review=read(H/'WORK_CURRENT_REVIEW.json')
review.update(at=datetime.datetime.now().astimezone().isoformat(),status='KINEMATICS_PASSED_PREPARE_PLUS2',current_job_kind='static_preparation',current_case_label='C +2deg preparation only; no hydrodynamic run',kinematic_sweep_accepted=True,kinematic_evidence=str(H/'audit/KINEMATIC_POC_REVIEW_20261103.json'),last_decision='Full100-step +/-5degree sweep passed native mesh/connectivity and clearance checks. Prepare +2degree from C0t0.650 with10 frozen-flow pose steps; no hydrodynamic steps authorized in this job.',next='Review prepared +2degree checkpoint and temporal restart treatment; keep later variants gated.',obstacle='No kinematic blocker. Quantitative grid/time, far-field and energy validation remain separate.',next_test='Prepare +2degree pose only, then inspect checkpoint; no fluid transient in this stage.')
review['not_established']=['Formal grid/time uncertainty remains unquantified.','Far-field velocity memory remains.','Matched original A control and quantitative energy validation remain separate.','No +2degree hydrodynamic solution yet.']
write(H/'NIGHT_QUEUE_STATE.json',state);write(H/'WORK_CURRENT_REVIEW.json',review);write(H/'NIGHT_QUEUE.json',cfg)
with (H/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=review['at'],kind='reviewed_static_preparation_authorized',job=job,backup=str(backup),previous_controller_pid=5016,previous_controller_stopped=True))+'\n')
print(json.dumps(dict(preparation_job_ready=job,backup=str(backup)),indent=2))
