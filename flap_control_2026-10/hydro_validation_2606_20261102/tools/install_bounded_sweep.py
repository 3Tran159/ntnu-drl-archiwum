from pathlib import Path
import sys,json,hashlib,shutil,datetime,csv
H=Path(__file__).resolve().parents[1];R=H.parent;E='BOUNDED_FIXED_PLUS2_SWEEP_20261103';D=R/'independent_cfd_diagnostics/C0_speed_down_20261103'
import night_queue as q
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
st=q.read(q.STATE);cfg=q.read(q.CFG);assert st.get('active') is None and not (H/'audit/night_queue.lock').exists()
assert st['failure_hold']=='SPEED_SWEEP_PLUS2_20261103_SMOKE'
assert not any(j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs'])
assert not any(p['ownedBatch'] for p in q.processes())
for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:assert not (R/name).exists()
source=D/'run_20261103_111057/checkpoint.sim';assert sha(source)=='7d140c9523f1e2eeb34875013d65424845def7d474df5a8b3562693b36e43d41'
out=H/'cases'/E;out.mkdir(exist_ok=False);dest=out/'approved_C0_t0690.sim';shutil.copy2(source,dest);assert sha(dest)==sha(source)
backup=H/'audit'/('before_bounded_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for rel in ['tools/night_queue.py','tools/night_native.py','tools/ramp_authorization.py','tools/night_dashboard.py','tools/cfd_control.py','NIGHT_QUEUE.json','WORK_CURRENT_REVIEW.json']:shutil.copy2(H/rel,backup/Path(rel).name)
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103','C0_SPEED_DOWN_20261103']","[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103','C0_SPEED_DOWN_20261103','BOUNDED_FIXED_PLUS2_SWEEP_20261103']")
patch('night_native.py',"name=sys.argv[1];", "allowed['BoundedFixedFlapSweep.java']=8\nname=sys.argv[1];")
marker="env={**os.environ,'NTNU_HYDRO_RUN_ID':stamp,'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_ROOT':str(h),'NTNU_HYDRO_MACRO_DIR':str(snapshot.parent)}"
patch('night_native.py',marker,marker+"\nif name=='BoundedFixedFlapSweep.java':\n from bounded_sweep_auth import authorize_environment\n env.update(authorize_environment(h,name,sim,cpu))")
patch('night_queue.py',"from ramp_authorization import blocks", "ALLOWED.add('BoundedFixedFlapSweep.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='c0_speeddown':", "  elif j.get('kind')=='bounded_sweep':\n   assert j['macro']=='BoundedFixedFlapSweep.java' and j.get('cpu_processes')==8\n   assert j.get('experiment_id')=='BOUNDED_FIXED_PLUS2_SWEEP_20261103' and j.get('angles_deg')==[0,2] and j.get('speeds_m_s')==[10,12,14,16,18]\n  elif j.get('kind')=='c0_speeddown':")
patch('night_queue.py',"def output_path(receipt):", "def output_path(receipt):\n if receipt['macro']=='BoundedFixedFlapSweep.java':return H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103'/('run_'+receipt['run_id'])")
patch('night_queue.py',"['speed_down_smoke_passed_not_scientific_validation'", "['bounded_sweep_complete','bounded_sweep_paused','speed_down_smoke_passed_not_scientific_validation'")
patch('night_queue.py'," atomic(H/'NIGHT_STATUS.json',base)", " if review.get('current_job_kind')=='bounded_sweep':\n  from bounded_sweep_dashboard import publish\n  publish(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
patch('night_dashboard.py'," if review0.get('current_job_kind')=='c0_speeddown':", " if review0.get('current_job_kind')=='bounded_sweep':\n  from bounded_sweep_dashboard import render\n  return render(h,view,base,review0)\n if review0.get('current_job_kind')=='c0_speeddown':")
patch('cfd_control.py',"['RAMP_C0_PLUS2_S5_20261103','SPEED_SWEEP_PLUS2_20261103']","['RAMP_C0_PLUS2_S5_20261103','SPEED_SWEEP_PLUS2_20261103','C0_SPEED_DOWN_20261103','BOUNDED_FIXED_PLUS2_SWEEP_20261103']")
props=H/'audit/BOUNDED_SWEEP_RUNTIME.properties';props.write_text(f'input={dest.as_posix()}\ntime_s=0.6900000000000005\niteration=12360\nstage=0\nstage_start_s=0.65\n',encoding='utf8')
macro=H/'macros/BoundedFixedFlapSweep.java';job=dict(id=E+'_RUN',kind='bounded_sweep',experiment_id=E,approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(dest),input_sha256=sha(dest),initial_time_s=.6900000000000005,cpu_processes=8,angles_deg=[0,2],speeds_m_s=[10,12,14,16,18],runtime_properties_sha256=sha(props),progress_timeout_s=900,maximum_runtime_s=86400,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_overset_error_cells=0,maximum_turbulent_viscosity_ratio=99999))
ap=H/'audit/BOUNDED_SWEEP_APPROVAL_20261103.json';approval=dict(at=q.now(),approved_by_user=True,experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[job['id']],source='Explicit current user NTNU CFD CONTINUE TO FIXED-FLAP VELOCITY SWEEP: authorize prepare and launch bounded staged campaign without further per-stage questions',scope='C0t0.690 no reset; same18to10 law; settleC0at10; smooth0to+2 at10; settle; fixed+2 U10/12/14/16/18; 8CPU noGPU dt0.002; no5deg/waves/DRL',inner_iterations=50,residual_threshold=.01,residual_nonpass_policy='Diagnostic samples only; no static point or subsequent measurement stage until force/residual stabilization passes. No reclassification of old omega test.',safety_thresholds_unchanged=True,retention='Only newly generated periodic recovery files: keep two after new SHA-verified save; preserve source, old checkpoints, stable+2U10 anchor and final result.',source_checkpoint=str(source),source_sha256=job['input_sha256'],macro_sha256=job['macro_sha256'],job=job)
q.atomic(ap,approval);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg['jobs'].append(job);cfg.update(accept_new_jobs=False,controller_exit_requested=False);q.atomic(q.CFG,cfg)
residual={}
for f in (D/'run_20261103_111057').glob('residual_final_*.csv'):
 with f.open() as stream:
  data=[]
  for row in csv.reader(stream):
   try:it=int(float(row[0]));v=float(row[1])
   except (ValueError,IndexError):continue
   if 12320<it<=12360:data.append((it,v))
 assert [r[0] for r in data]==list(range(12321,12361));residual[f.stem.removeprefix('residual_final_')]=dict(first_iteration=data[0][0],last_iteration=data[-1][0],count=40,ratio=data[-1][1]/data[0][1])
q.atomic(H/'audit/BOUNDED_SWEEP_RESIDUAL_AUDIT.json',dict(at=q.now(),previous_window_correct=True,monitors=residual,previous_Sdr_test_remains_not_passed=True,new_inner_iterations=50,new_window_method='Native monitor X/Y samples; exactly iteration_before+1 through iteration_after, require50 contiguous samples',new_threshold=.01))
work=q.read(H/'WORK_CURRENT_REVIEW.json');work.update(at=q.now(),status='BOUNDED_SWEEP_AUTHORIZED',current_job_kind='bounded_sweep',current_case_label='C0 decelerate / settle / flap+2 / velocity sweep',last_decision='New explicitly authorized bounded diagnostic-to-static pipeline;50inner, same safety guards. Auto advance only with required stage gates. Old failures untouched.',obstacle='Actual deceleration safety and settled+2U10 remain to be demonstrated',next='Start bounded pipeline; no manual short-stage approval stops',parameters={**work.get('parameters',{}),'CPU_max':8,'dt':.002,'inner':50,'U':17.93152,'delta':0});q.atomic(H/'WORK_CURRENT_REVIEW.json',work)
q.event('bounded_pipeline_prepared_explicit_user_approval',job=job,backup=str(backup));print(json.dumps(dict(job=job['id'],input=str(dest),resources=q.resources(),prepared=True),indent=2))
