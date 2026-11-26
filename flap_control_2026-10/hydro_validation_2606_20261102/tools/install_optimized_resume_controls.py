from pathlib import Path
import shutil,py_compile
import night_queue as q
h=q.H;d=h/'cases/RECOVERED_PERF_20261103';assert not q.read(q.STATE).get('active') and not q.LOCK.exists()
def patch(p,a,b):
 t=p.read_text();assert t.count(a)==1,(p.name,a);p.write_text(t.replace(a,b),encoding='utf8')
p=h/'tools/recovered_sweep_control.py';shutil.copy2(p,d/'before_production_config/recovered_sweep_control.py')
patch(p,"H=Path(__file__).resolve().parents[1];E='RECOVERED_FIXED_PLUS2_SWEEP_20261103'", "H=Path(__file__).resolve().parents[1];OPT=any(j.get('macro')=='OptimizedRecoveredSweep.java' for j in q.read(q.CFG)['jobs']);E='RECOVERED_PERF_20261103' if OPT else 'RECOVERED_FIXED_PLUS2_SWEEP_20261103'\nMACRO='OptimizedRecoveredSweep.java' if OPT else 'RecoveredFixedFlapSweep.java'\nPROPS=H/'audit'/('OPTIMIZED_RECOVERED_RUNTIME.properties' if OPT else 'RECOVERED_SWEEP_RUNTIME.properties')\nAPPROVAL=H/'cases/RECOVERED_PERF_20261103/PRODUCTION_RESUME_APPROVAL.json' if OPT else H/'audit/RECOVERED_SWEEP_APPROVAL_20261103.json'")
patch(p,"runs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]", "runs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('macro')==MACRO and r.get('output')]")
patch(p,"ap=H/'audit/RECOVERED_SWEEP_APPROVAL_20261103.json';a=q.read(ap)","ap=APPROVAL;a=q.read(ap)")
patch(p,"macro=H/'macros/RecoveredFixedFlapSweep.java';assert sha(macro)==a['macro_sha256']", "macro=H/'macros'/MACRO;assert sha(macro)==(a['job']['macro_sha256'] if OPT else a['macro_sha256'])")
patch(p,"props=H/'audit/RECOVERED_SWEEP_RUNTIME.properties'", "props=PROPS")
patch(p,"a['approved_job_ids'].append(j['id'])", "j['source_job_id']=last['id'];a['approved_job_ids'].append(j['id'])")
patch(p,"assert st['active'].get('experiment_id')==E,'Another owned task is active'", "assert st['active'].get('experiment_id')==E and st['active'].get('macro')==MACRO,'Another owned task is active'")
patch(p,"assert len(pending)==1 and pending[0].get('experiment_id')==E,'Unexpected queue scope'", "assert len(pending)==1 and pending[0].get('experiment_id')==E and pending[0].get('macro')==MACRO,'Unexpected queue scope'")
patch(p,"assert j['cpu_processes']==8 and sha(H/'audit/RECOVERED_SWEEP_RUNTIME.properties')==j['runtime_properties_sha256']", "assert j['cpu_processes']==(q.read(H/'cases/RECOVERED_PERF_20261103/SELECTED_CONFIG.json')['cpu_processes'] if OPT else 8) and sha(PROPS)==j['runtime_properties_sha256']")
patch(p,"time_s=j['initial_time_s'],CPU=8,GPU=False", "time_s=j['initial_time_s'],CPU=j['cpu_processes'],GPU=False")
p=h/'tools/optimized_recovered_auth.py';shutil.copy2(p,d/'before_production_config/optimized_recovered_auth.py')
patch(p,"assert j['input_sha256']==plan['input_sha256'] and sim==Path(plan['production_checkpoint']['path'])", "assert j['source_role']=='production_checkpoint'\n if sim==Path(plan['production_checkpoint']['path']):assert j['input_sha256']==plan['input_sha256']\n else:\n  previous=st['jobs'].get(j.get('source_job_id'),{});assert previous.get('macro')=='OptimizedRecoveredSweep.java' and (previous.get('macro_status') or {}).get('status')=='bounded_sweep_paused'\n  assert sim==Path(previous['output'])/'paused_checkpoint.sim'\n  metadata=read(sim.with_suffix('.sim.json'));verified=st['checkpoint_integrity'].get(str(sim),{})\n  assert verified.get('native_save_complete') and metadata['sha256']==verified['sha256']==j['input_sha256']\n  assert abs(metadata['time_s']-j['initial_time_s'])<1e-9")
p=h/'tools/cfd_control.py'
# Only display the scoped actual maximum; legacy launch caps remain unchanged.
patch(p,"maximum_cpu=8 if selected", "maximum_cpu=selected['cpu_processes'] if selected and selected.get('experiment_id')=='RECOVERED_PERF_20261103' else 8 if selected")
for name in ['recovered_sweep_control.py','optimized_recovered_auth.py','cfd_control.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
q.event('optimized_manual_controls_installed',launcher=str(h.parent/'START_RECOVERED_FLAP_SWEEP.cmd'),manual_pause_only=True,safety_hold_auto_release=False)
print('Existing START_RECOVERED_FLAP_SWEEP supports selected production and verified manual-pause lineage; safety HOLD remains blocked.')
