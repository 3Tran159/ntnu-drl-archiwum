from pathlib import Path
import subprocess,json,datetime,py_compile,shutil,hashlib
h=Path(__file__).resolve().parents[1]
p=h/'macros/PrepareC0OverlapRefinement.java';s=p.read_text(encoding='utf8')
# Prepared but never executed earlier. Use original C numerical method, isolating the spatial change.
s=s.replace('OversetMeshInterpolationOption.Type.DISTANCE','OversetMeshInterpolationOption.Type.LINEARQUASI2D')
s=s.replace('Interface uses DISTANCE, matching current distance diagnostic.','Interface uses LINEARQUASI2D, matching the original C0 control.')
s=s.replace('distance_weighted_set=','linear_quasi2D_set=')
p.write_text(s,encoding='utf8')
r=subprocess.run(['C:/Program Files/Eclipse Adoptium/jdk-25.0.3.9-hotspot/bin/javac.exe','-encoding','UTF-8','-cp','E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/star/lib/java/platform/modules/ext/*','-d',str(h/'macros/compiled'),str(p)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,r.stderr
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup=h/'runs/controller_snapshots'/stamp;backup.mkdir(parents=True)
for name in ['night_native.py','night_queue.py','night_dashboard.py']:shutil.copy2(h/'tools'/name,backup/name)
p=h/'tools/night_native.py';s=p.read_text(encoding='utf8').replace("'FreshC0NoFluxInit.java':8}","'FreshC0NoFluxInit.java':8,'PrepareC0OverlapRefinement.java':8}");assert "'PrepareC0OverlapRefinement.java':8" in s;p.write_text(s,encoding='utf8')
p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8').replace("'FreshC0NoFluxInit.java'}","'FreshC0NoFluxInit.java','PrepareC0OverlapRefinement.java'}")
s=s.replace("'FreshC0NoFluxInit.java':'c0_fresh_noflux_',","'PrepareC0OverlapRefinement.java':'c0_overlap1mm_','FreshC0NoFluxInit.java':'c0_fresh_noflux_',")
s=s.replace("metrics['operation']='STEADY_INITIALIZATION' if steady else","metrics['operation']='MESH_PREPARATION' if rec['macro'].startswith('Prepare') else 'STEADY_INITIALIZATION' if steady else")
s=s.replace("['inspection_complete','steady_diagnostic_ready']","['inspection_complete','steady_diagnostic_ready','mesh_connectivity_prepared']")
p.write_text(s,encoding='utf8')
p=h/'tools/night_dashboard.py';s=p.read_text(encoding='utf8').replace("case={'FreshC0NoFluxInit.java'","case={'PrepareC0OverlapRefinement.java':'C0 — lokalna poprawa siatki Overset przed zawiasem; bez kroków przepływu','FreshC0NoFluxInit.java'")
s=s.replace('To diagnostyka, nie zaakceptowany model.','Ten test zatrzymał próg ciśnienia po10 iteracjach, więc nie rozstrzyga wpływu korekty strumieni. Następny etap: lokalna siatka1mm w obszarze nakładania przed zawiasem, przy oryginalnej interpolacji LinearQuasi2D. Najpierw pełna kontrola łączności i tożsamości siatki tła.')
p.write_text(s,encoding='utf8')
for name in ['night_queue.py','night_native.py','night_dashboard.py']:py_compile.compile(str(h/'tools'/name),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'))
source=h/'cases/SP_C_split0_overset/SP_C_build_error_20261102_191807.sim'
job=dict(id='c0_overlap1mm_mesh',macro='PrepareC0OverlapRefinement.java',input=str(source),initial_time_s=0,angle_deg=0,approved=True,purpose='Local Overset source resolution1mm ahead of hinge, same geometry/cage/background source; original LinearQuasi2D control. Mesh-only preparation, require full connectivity and separate background mesh identity review before flow.')
assert all(j['id']!=job['id'] for j in cfg['jobs']);cfg['jobs'].append(job)
cfg.setdefault('release_failure_hold',{})['c0_fresh_no_flux_init']='Early pressure-screen failure at10 iterations, not evidence of asymptotic divergence or proof against flux correction. Preserve test. Approve mesh-only local overlap diagnostic.'
cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
ev=dict(at=datetime.datetime.now().astimezone().isoformat(),kind='work_scientific_decision',previous_job='c0_fresh_no_flux_init',conclusion='inconclusive_pressure_screen_stopped_10_iterations',next_job=job,source_sha256=hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),scientific_gate=False)
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(ev)+'\n')
with (h/'NIGHT_LOG.md').open('a',encoding='utf8') as f:f.write('\n'+ev['at']+' No-flux startup stopped by the tighter5MPa pressure guard after10 iterations, before a trend can establish. Do NOT claim flux correction was excluded. Archived B startup also had unphysical early pseudo-iteration pressure; old C initial k/omega were uniform before steady solving, so inherited turbulence from the motion test is not established as the cause. Next: local overlap mesh resolution1mm; mesh-only audit first. Original LinearQuasi2D retained for comparison with original C0. No physical geometry change.\n')
(h/'cases/SP_C_split0_overset/c0_fresh_noflux_20261103_001005/work_conclusion.json').write_text(json.dumps(ev,indent=2),encoding='utf8')
print(json.dumps(ev,indent=2))
