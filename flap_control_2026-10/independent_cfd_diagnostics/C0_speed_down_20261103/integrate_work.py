from pathlib import Path
import sys,json,hashlib,shutil,datetime,subprocess
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'tools'));import night_queue as q
E='C0_SPEED_DOWN_20261103';J=E+'_SMOKE'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
st=q.read(q.STATE);cfg=q.read(q.CFG)
assert st.get('active') is None and not (H/'audit/night_queue.lock').exists(),'Wait for graceful idle controller exit'
assert st['failure_hold']=='SPEED_SWEEP_PLUS2_20261103_SMOKE' and cfg['accept_new_jobs'] is False
assert not any(j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs'])
candidate=q.read(D/'CANDIDATE.json');pre=q.read(D/'PRELAUNCH_AUDIT.json');assert all(pre['checks'].values())
original=D/'C0SpeedDownSmoke.java';assert sha(original)==candidate['candidate_sha256']
source=H/'cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim'
assert sha(source)=='c8b2396f2d087112d06045b06a6c62e93c4003eafde969aa8c8d0ca8120afc10'
assert not any(p['ownedBatch'] for p in q.processes())
rs=q.resources();assert rs['disk_free_GiB']>=18 and rs['ram_available_GiB']>=16
for n in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:assert not (H.parent/n).exists()
backup=D/('integration_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for f in ['tools/night_queue.py','tools/night_native.py','tools/ramp_authorization.py','tools/night_dashboard.py','NIGHT_QUEUE.json','WORK_CURRENT_REVIEW.json','macros/C0SpeedDownSmoke.java']:
 if (H/f).exists():shutil.copy2(H/f,backup/Path(f).name)
text=original.read_text();old='mass.getParts().setObjects(outer);';assert text.count(old)==1
text=text.replace(old,old+'\nMassFlowReport inletMass=s.getReportManager().createReport(MassFlowReport.class);List<Boundary> inlets=new ArrayList<>();for(Boundary b:outer)if(b.getBoundaryType() instanceof InletBoundary)inlets.add(b);if(inlets.isEmpty())throw new IllegalStateException("Missing inlet");inletMass.getParts().setObjects(inlets);')
assert text.count('/10800.')==1;text=text.replace('/10800.','/Math.abs(inletMass.getReportMonitorValue())')
text=text.replace('"ramp_paused":"ramp_failed"','"c0_speeddown_paused":"c0_speeddown_failed"').replace('note("Ramp step="','note("C0 speed-down step="')
macro=H/'macros/C0SpeedDownSmoke.java';macro.write_text(text,encoding='utf8')
build=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(macro)],capture_output=True,text=True,check=True)
(D/'WORK_COMPILE.txt').write_text(build.stderr)
def patch(name,a,b):
 p=H/'tools'/name;t=p.read_text();assert t.count(a)==1,(name,a);p.write_text(t.replace(a,b),encoding='utf8')
patch('ramp_authorization.py',"[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103']","[EXPERIMENT,'SPEED_SWEEP_PLUS2_20261103','C0_SPEED_DOWN_20261103']")
patch('night_native.py',"name=sys.argv[1];", "allowed['C0SpeedDownSmoke.java']=8\nname=sys.argv[1];")
marker="env={**os.environ,'NTNU_HYDRO_RUN_ID':stamp,'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_ROOT':str(h),'NTNU_HYDRO_MACRO_DIR':str(snapshot.parent)}"
patch('night_native.py',marker,marker+"\nif name=='C0SpeedDownSmoke.java':\n from c0_speeddown_auth import authorize_environment\n env.update(authorize_environment(h,name,sim,cpu))")
patch('night_queue.py',"from ramp_authorization import blocks", "ALLOWED.add('C0SpeedDownSmoke.java')\nfrom ramp_authorization import blocks")
patch('night_queue.py',"  elif j.get('kind')=='speed_sweep':", "  elif j.get('kind')=='c0_speeddown':\n   assert j['macro']=='C0SpeedDownSmoke.java' and j.get('cpu_processes')==8 and j.get('angle_deg')==0\n   assert j.get('experiment_id')=='C0_SPEED_DOWN_20261103'\n  elif j.get('kind')=='speed_sweep':")
patch('night_queue.py',"def output_path(receipt):", "def output_path(receipt):\n if receipt['macro']=='C0SpeedDownSmoke.java':return H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103'/('run_'+receipt['run_id'])")
patch('night_queue.py',"['speed_smoke_passed','speed_sweep_complete'", "['speed_down_smoke_passed_not_scientific_validation','c0_speeddown_paused','speed_smoke_passed','speed_sweep_complete'")
patch('night_queue.py'," atomic(H/'NIGHT_STATUS.json',base)", " if review.get('current_job_kind')=='c0_speeddown':\n  from c0_speeddown_dashboard import publish\n  publish(H,view,base,st,review)\n  atomic(H/'NIGHT_DASHBOARD.json',view)\n atomic(H/'NIGHT_STATUS.json',base)")
patch('night_dashboard.py'," if review0.get('current_job_kind')=='speed_sweep':", " if review0.get('current_job_kind')=='c0_speeddown':\n  from c0_speeddown_dashboard import render\n  return render(h,view,base,review0)\n if review0.get('current_job_kind')=='speed_sweep':")
ap=H/'audit/C0_SPEED_DOWN_EXPLICIT_APPROVAL_20261103.json'
job=dict(id=J,kind='c0_speeddown',experiment_id=E,approved=True,macro=macro.name,macro_sha256=sha(macro),input=str(source),input_sha256=sha(source),initial_time_s=.65,cpu_processes=8,angle_deg=0,progress_timeout_s=900,maximum_runtime_s=1800,runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_overset_error_cells=0,maximum_turbulent_viscosity_ratio=99999))
approval=dict(approved_by_user=True,source='Current explicit user instruction to integrate/run only20-step C0_SPEED_DOWN_20261103; prepare continuation launcher only ifPASS',experiment_id=E,previous_blocked_job=st['failure_hold'],previous_case_remains_failed=True,approved_job_ids=[J],scope='20steps from native verified C0t0.650; fixed0deg; no reset; same safeguards;8CPU/noGPU; no long campaign or full sweep',candidate_sha256=candidate['candidate_sha256'],executable_macro_sha256=job['macro_sha256'],integration_correction='Only executable copy: mass imbalance normalized by actual inlet mass flow instead of18m/s constant; same1e-4 threshold; distinctive diagnostic outcome labels',job=job,at=q.now())
q.atomic(ap,approval);cfg.setdefault('experiment_authorizations',{})[E]=dict(approved=True,previous_blocked_job=st['failure_hold'],evidence=str(ap));cfg['jobs'].append(job);cfg.update(accept_new_jobs=False,controller_exit_requested=False);q.atomic(q.CFG,cfg)
review=q.read(H/'WORK_CURRENT_REVIEW.json');review.update(at=q.now(),status='C0_SPEEDDOWN_PREFLIGHT',current_job_kind='c0_speeddown',current_case_label='C0 fixed0deg U18 toward10 smoke20steps',last_decision='User-authorized independent20-step test; previousFAILs and full sweep remain blocked. No reset of source fields.',obstacle='Native20-step smoke pending',next='Review saved checkpoint after20steps; no automatic long continuation',parameters={**review.get('parameters',{}),'CPU_max':8,'U':18,'delta':0});q.atomic(H/'WORK_CURRENT_REVIEW.json',review)
q.atomic(D/'WORK_INTEGRATION.json',dict(at=q.now(),job=job,backup=str(backup),original_candidate_preserved=True,correction=approval['integration_correction'],preflight_resources=rs,registered=True,launched=False));q.event('c0_speeddown_integrated_current_user_authorization',job=job)
print(json.dumps(dict(job=J,registered=True,source_sha256=job['input_sha256'],macro_sha256=job['macro_sha256'],resources=rs),indent=2))
