"""Register exactly one authorized verification in the existing serial controller."""
from pathlib import Path
import json,hashlib,shutil,datetime,py_compile
import night_queue as q
H=q.H;R=H.parent;E='INLET_PRESSURE_RECOVERY_20261103';D=R/'independent_cfd_diagnostics/INLET_PRESSURE_AUDIT_20261103'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
st=q.read(q.STATE);cfg=q.read(q.CFG)
assert st.get('active') is None and not q.LOCK.exists()
assert st['failure_hold']=='BOUNDED_FIXED_PLUS2_SWEEP_20261103_RUN'
assert not any(p['ownedBatch'] for p in q.processes())
assert not any(j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs'])
source=H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103/approved_C0_t0690.sim'
assert sha(source)=='7d140c9523f1e2eeb34875013d65424845def7d474df5a8b3562693b36e43d41'
failure=H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103/run_20261103_113904/error_checkpoint.sim'
assert sha(failure)=='472cee3cc6ce35dbc7d3901954134eb1348179212aa98e717d7e14fb9b591971'
assert q.resources()['disk_free_GiB']>=15
backup=H/'audit'/('before_pressure_recovery_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for name in ['tools/night_queue.py','tools/night_native.py','tools/ramp_authorization.py','tools/night_dashboard.py','tools/cfd_control.py','NIGHT_QUEUE.json','WORK_CURRENT_REVIEW.json']:shutil.copy2(H/name,backup/Path(name).name)
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"'BOUNDED_FIXED_PLUS2_SWEEP_20261103']","'BOUNDED_FIXED_PLUS2_SWEEP_20261103','INLET_PRESSURE_RECOVERY_20261103']")
patch('night_native.py','name=sys.argv[1];',"allowed['InletPressureRecovery.java']=8\nname=sys.argv[1];")
patch('night_native.py',"if name=='BoundedFixedFlapSweep.java':","if name=='InletPressureRecovery.java':\n from pressure_recovery_auth import authorize_environment\n env.update(authorize_environment(h,name,sim,cpu))\nif name=='BoundedFixedFlapSweep.java':")
patch('night_queue.py',"from ramp_authorization import blocks", "ALLOWED.add('InletPressureRecovery.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='bounded_sweep':","  elif j.get('kind')=='pressure_recovery':\n   assert j['macro']=='InletPressureRecovery.java' and j.get('cpu_processes')==8 and j.get('angle_deg')==0\n   assert j.get('experiment_id')=='INLET_PRESSURE_RECOVERY_20261103' and j.get('max_steps')==50\n  elif j.get('kind')=='bounded_sweep':")
patch('night_queue.py','def output_path(receipt):',"def output_path(receipt):\n if receipt['macro']=='InletPressureRecovery.java':return H/'cases/INLET_PRESSURE_RECOVERY_20261103'/('run_'+receipt['run_id'])")
patch('night_queue.py',"['bounded_sweep_complete'","['pressure_recovery_complete','pressure_recovery_paused','bounded_sweep_complete'")
patch('night_queue.py'," if review.get('current_job_kind')=='bounded_sweep':"," if review.get('current_job_kind')=='pressure_recovery':\n  from pressure_recovery_dashboard import publish\n  publish(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n if review.get('current_job_kind')=='bounded_sweep':")
patch('night_dashboard.py'," if review0.get('current_job_kind')=='bounded_sweep':"," if review0.get('current_job_kind')=='pressure_recovery':\n  from pressure_recovery_dashboard import render\n  return render(h,view,base,review0)\n if review0.get('current_job_kind')=='bounded_sweep':")
patch('cfd_control.py',"'BOUNDED_FIXED_PLUS2_SWEEP_20261103']","'BOUNDED_FIXED_PLUS2_SWEEP_20261103','INLET_PRESSURE_RECOVERY_20261103']")
p=H/'tools/pressure_recovery_dashboard.py';t=(H/'tools/bounded_sweep_dashboard.py').read_text()
t=t.replace('BOUNDED_FIXED_PLUS2_SWEEP_20261103',E).replace('BOUNDED_SWEEP','PRESSURE_RECOVERY').replace('bounded_sweep','pressure_recovery').replace('Bounded fixed+2 velocity sweep','C0 inlet pressure recovery: 50 steps').replace('klapka +2°, sweep prędkości','C0: kontrola łagodniejszego hamowania')
t=t.replace("approved_scope='0deg decel/settle10; smooth+2 at10; fixed+2 U10,12,14,16,18'","approved_scope='Single 50-step deceleration repair, delta0, no following stages'")
t=t.replace('Etapy automatyczne: C0→10m/s · ustalenie · rampa+2° · ustalenie · 12/14/16/18m/s.','Wyłącznie 50 kroków kontroli poprawki. Dalsza kampania zablokowana do oceny.')
p.write_text(t,encoding='utf8')
props=H/'audit/PRESSURE_RECOVERY_RUNTIME.properties';props.write_text(f'input={source.as_posix()}\ntime_s=0.6900000000000005\niteration=12360\nstage=0\nstage_start_s=0.65\n',encoding='utf8')
macro=H/'macros/InletPressureRecovery.java'
job=dict(id=E+'_TEST',kind='pressure_recovery',experiment_id=E,approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(source),input_sha256=sha(source),initial_time_s=.6900000000000005,cpu_processes=8,angle_deg=0,max_steps=50,runtime_properties_sha256=sha(props),progress_timeout_s=900,maximum_runtime_s=3600,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_overset_error_cells=0,maximum_turbulent_viscosity_ratio=99999))
ap=H/'audit/PRESSURE_RECOVERY_APPROVAL_20261103.json'
approval=dict(at=q.now(),approved_by_user=True,experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[job['id']],source='Explicit user INLET PRESSURE FAILURE ROOT CAUSE AND RECOVERY: at most one short corrective test after evidence-based audit',scope='50 physical steps from good C0 t0.690, delta0; C2 slowing of existing quintic; dt0.002,50inner,8CPU,noGPU; no automatic campaign continuation',root_cause_evidence=str(D/'FIELD_AUDIT.json'),safety_thresholds_unchanged=True,pressure_global_included=True,job=job)
q.atomic(ap,approval);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg['jobs'].append(job);cfg.update(accept_new_jobs=False,controller_exit_requested=False)
# Verify modifications before making the new job eligible.
for p in (H/'tools').glob('*.py'):
 if p.name in ['night_queue.py','night_native.py','ramp_authorization.py','night_dashboard.py','cfd_control.py','pressure_recovery_auth.py','pressure_recovery_dashboard.py']:py_compile.compile(str(p),doraise=True)
q.atomic(q.CFG,cfg)
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),status='PRESSURE_RECOVERY_TEST_PREPARED',current_job_kind='pressure_recovery',current_case_label='C0 inlet pressure recovery: one 50-step test',last_decision='Inertial pressure response tracks imposed deceleration (R2>0.99999998); test only C2 slowing, same fields, same global safety guards. No following stages.',obstacle='Pressure recovery and residuals must pass the controlled verification',next='Single 50-step test from t0.690; hold for review afterwards',next_test='INLET_PRESSURE_RECOVERY_20261103_TEST',scientific_approved=False,training_eligible=False);q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.event('pressure_recovery_single_test_prepared',job=job,backup=str(backup))
print(json.dumps(dict(prepared=True,job=job['id'],resources=q.resources(),source_sha256=job['input_sha256'],failed_checkpoint_sha256=sha(failure)),indent=2))
