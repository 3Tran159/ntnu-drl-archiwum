from pathlib import Path
import json,hashlib,datetime,sys,re,csv
import night_queue as q
H=Path(__file__).resolve().parents[1];E='RAMP_C0_PLUS2_S5_20261103';st=q.read(q.STATE);cfg=q.read(q.CFG)
assert st.get('active') is None
rec=st['jobs'][E+'_SMOKE'];out=Path(rec['output']);status=q.read(out/'status.json');assert rec['state']=='completed' and status['status']=='ramp_smoke_passed'
with (out/'history.csv').open() as f:rows=list(csv.DictReader(f))
assert len(rows)==5 and abs(float(rows[-1]['time_s'])-.66)<1e-9
for r in rows:
 t=float(r['time_s']);u=(t-.65)/.2;a=2*(10*u**3-15*u**4+6*u**5)
 assert abs(float(r['flap_angle_deg'])-a)<1e-9 and abs(float(r['measured_angle_deg'])-a)<1e-5 and float(r['center_error_m'])<1e-7
 assert float(r['p_absolute_min_Pa'])>12339.214766776897 and float(r['mass_imbalance_relative'])<1e-4
 assert float(r['omega_floor_cells'])==float(r['k_floor_cells'])==float(r['overset_error_cells'])==0
 assert float(r['min_volume_m3'])>0 and float(r['min_cell_quality'])>0
audit=(out/'full_audit_final.txt').read_text();assert 'total=333939' in audit and 'errors=0 difficult_interpolation=0' in audit
cp=out/'checkpoint.sim';meta=st['checkpoint_integrity'][str(cp)];assert meta['native_save_complete']
with cp.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==meta['sha256']
pre=q.read(out/'preflight.json');assert pre['flow_frozen'] is False and pre['iteration']==11560 and pre['time']<.6500001
assert abs(pre['initial_CL']-.3256530206195925)<1e-9 and abs(pre['initial_CD']-.007244510839521137)<1e-9
review=dict(at=q.now(),passed=True,scope='Five active URANS timesteps and native motion/connectivity; full ramp and hold remain untested',input_time_s=.65,end_time_s=.66,iteration=int(rows[-1]['native_iteration']),angle_deg=float(rows[-1]['flap_angle_deg']),angular_rate_deg_s=float(rows[-1]['flap_angular_velocity_deg_s']),minimum_absolute_pressure_Pa=min(float(r['p_absolute_min_Pa']) for r in rows),maximum_mass_imbalance=max(float(r['mass_imbalance_relative']) for r in rows),minimum_volume_m3=min(float(r['min_volume_m3']) for r in rows),maximum_center_error_m=max(float(r['center_error_m']) for r in rows),final_CL=float(rows[-1]['CL_hydro']),final_CD=float(rows[-1]['CD']),final_Mh=float(rows[-1]['Mh_Nm']),checkpoint=str(cp),sha256=digest,bytes=cp.stat().st_size,old_step_case_still_failed=True)
q.atomic(H/'audit/RAMP_SMOKE_REVIEW_20261103.json',review)
macro=H/'macros/RampPlus2Run.java';job=dict(id=E+'_RUN',kind='ramp',experiment_id=E,approved=True,macro=macro.name,macro_sha256=hashlib.sha256(macro.read_bytes()).hexdigest(),input=str(cp),input_sha256=digest,initial_time_s=.66,cpu_processes=8,angle_deg=2,progress_timeout_s=900,maximum_runtime_s=7200)
assert not any(j['id']==job['id'] for j in cfg['jobs']);cfg['jobs'].append(job);cfg['accept_new_jobs']=False
props=f'input={cp.as_posix()}\ntime_s=0.66\niteration={review["iteration"]}\nsha256={digest}\n'
(H/'audit/RAMP_PLUS2_RUNTIME.properties').write_text(props,encoding='utf8')
ap=H/'audit/RAMP_PLUS2_EXPLICIT_APPROVAL_20261103.json';approval=q.read(ap);approval['approved_job_ids'].append(job['id']);approval.update(smoke_review=str(H/'audit/RAMP_SMOKE_REVIEW_20261103.json'),continuation_condition_satisfied=True,continued_job=job);q.atomic(ap,approval);q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(last_decision='Five active URANS ramp steps passed. Continuation prepared from t0.660 checkpoint; not launched. Old step+2 failure remains blocked.',obstacle='No short-start blocker. Full0.2s ramp/hold and automatic stability criterion still require actual run.',next='User runs F:\\ntnu\\flap_control\\START_RAMP_PLUS2.cmd; one existing controller executes only approved ramp/hold.');q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.event('ramp_smoke_passed_continuation_prepared_not_started',review=review,job=job)
print(json.dumps(review,indent=2))
