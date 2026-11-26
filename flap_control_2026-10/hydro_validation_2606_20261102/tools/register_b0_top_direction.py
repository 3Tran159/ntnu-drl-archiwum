from pathlib import Path
import json,datetime,hashlib,shutil,py_compile,subprocess
h=Path(__file__).resolve().parents[1];read=lambda p:json.loads(p.read_text(encoding='utf8'))
state=read(h/'NIGHT_QUEUE_STATE.json');assert not state.get('active'),'Wait for ownedC completion'
decision=read(h/'audit/B0_matched_top_followup_decision.json');assert decision['diagnostic_approved'] and not decision['scientific_approved']
assert not (h.parent/'STOP_OWNED_CFD.json').exists() and not (h.parent/'PAUSED_FOR_HOME.json').exists()
candidate=read(h/'audit/B0_top_direction_candidate.json');macro=Path(candidate['macro']);source=Path(candidate['source'])
assert macro.name=='B0URANSTopDirection.java' and hashlib.sha256(macro.read_bytes()).hexdigest()==candidate['macro_sha256']
with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==candidate['source_sha256']
c=state['jobs']['c0_top_backflow_extrapolated'];assert c['state']=='completed' and c['macro_status']['status']=='urans_diagnostic_ready'
review=read(Path(c['output'])/'work_review.json');assert all(review['whole_run_guards'].values())
backup=h/'runs/controller_snapshots'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
for f in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/f,backup/f)
for file,needle,replacement in [('night_native.py','allowed={',"{'B0URANSTopDirection.java':8,"),('night_queue.py','ALLOWED={',"{'B0URANSTopDirection.java',"),('night_dashboard.py','case={',"{'B0URANSTopDirection.java':'B0 — dopasowane warunki górnej granicy',")]:
 p=h/'tools'/file;s=p.read_text(encoding='utf8');assert macro.name not in s
 s=s.replace(needle,needle[:-1]+replacement,1)
 if file=='night_native.py':
  needle="assert name in ['InspectPressureOutlets.java','InspectHydroComparison.java','InspectBMatchingNumerics.java'] or variant=='SP_C'"
  assert needle in s;s=s.replace(needle,"assert name in ['B0URANSTopDirection.java','InspectPressureOutlets.java','InspectHydroComparison.java','InspectBMatchingNumerics.java'] or variant=='SP_C'")
 if file=='night_queue.py':
  needle="def output_path(receipt):"
  assert needle in s;s=s.replace(needle,needle+"\n if receipt['macro']=='B0URANSTopDirection.java':return H/'cases/SP_B_split0_fixed'/('b0_top_direction_'+receipt['run_id'])")
 p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
p=h/'NIGHT_QUEUE.json';cfg=read(p);assert not cfg['scientific_gates']['C0_bias_explained_and_approved']
job=dict(id='b0_matched_top_backflow',macro=macro.name,input=str(source),initial_time_s=.3,angle_deg=0,approved=True,purpose=candidate['changes'],runtime_guards=dict(minimum_absolute_pressure_Pa=12339.214766776897,maximum_mass_imbalance_relative=1e-4,maximum_omega_floor_cells=0,maximum_k_floor_cells=0,maximum_turbulent_viscosity_ratio=99999))
assert not any(x['id']==job['id'] for x in cfg['jobs']);cfg['jobs'].append(job);cfg['controller_exit_requested']=True
tmp=p.with_suffix('.work_tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(p)
event=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_matched_B_top_boundary_followup_registered',job=job,macro_sha256=candidate['macro_sha256'],source_sha256=candidate['source_sha256'],scientific_approved=False,angle_gate_closed=True)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(event)+'\n')
print(json.dumps(event,indent=2))
