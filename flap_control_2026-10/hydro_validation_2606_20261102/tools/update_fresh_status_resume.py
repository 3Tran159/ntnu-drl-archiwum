from pathlib import Path
import json,datetime,py_compile,shutil
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
old="base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"
new="""if active and not view['metrics'].get('last_output_sim'):
  fallback=view['flow_metrics']
  if fallback.get('last_output_sim'):base['last_checkpoint']=fallback['last_output_sim']
  if fallback.get('checkpoint_integrity'):base['last_checkpoint_integrity']=fallback['checkpoint_integrity']
 if active and active['macro']=='FreshC0DistanceInit.java':
  base['dt_s']=None;base.pop('timestep',None);base['last_solved_case']='C0 fresh DISTANCE initialization, 361532 cells';base['time_note']='Separate steady numerical initialization at physical time 0; previous transient checkpoint preserved'
 base['current_obstacle']='C0 force bias and turbulence clipping unresolved; no deflections approved'"""
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
cfgp=h/'NIGHT_QUEUE.json';cfg=json.loads(cfgp.read_text(encoding='utf8'));cfg['controller_exit_requested']=True
tmp=cfgp.with_suffix('.json.tmp');tmp.write_text(json.dumps(cfg,indent=2),encoding='utf8');tmp.replace(cfgp)
doc=h.parent/'HOME_RESUME_INSTRUCTIONS.md'
shutil.copy2(doc,h/'audit/HOME_RESUME_INSTRUCTIONS_before_20261103_0002.md')
txt=doc.read_text(encoding='utf8')
a=txt.index('## Current experiment');b=txt.index('## Exact execution environment')
txt=txt[:a]+r'''## Current experiment — 2026-11-03 00:02
FreshC0DistanceInit.java, launch 20261103_000031:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_distance_fresh_20261103_000031

Separate diagnostic from the protected pre-motion mesh:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\SP_C_mesh_ready.sim
SHA256: 8d4692832503adba9a8dca8b1583c56ea57a6f5979c2887b3dca1a70bb8f8eb6.

Purpose: distinguish inherited anomalous solution fields from a same-mesh Overset problem. Fresh initialization is performed only on this exact hash-matched uninitialized source, never on a solved checkpoint. Geometry and mesh remain unchanged. Static 0 degrees, gap 2.5 mm, 361532 cells, U18 m/s, rho1000, mu.001, Re2.142e7, SST, distance interpolation and flux correction.

This stage is STEADY numerical initialization. Physical time remains 0 s; actual progress is proven by increasing iteration in steady_iterations.csv. Cap 1500 iterations, checkpoint/fields/full connectivity every250. Stop for Work review after force stabilization or cap. No automatic transient conversion or deflections. The source and previous transient solutions are preserved.

## Latest preserved transient checkpoint
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_distance_20261102_232050\checkpoint.sim
- Time .6644 s, dt .002 s, timestep333, iteration9506.
- 729271037 bytes; SHA256 e3594c9b927545954e305d5b062672dec93f3a418df2a1ebe99885b6c2c5f375.
- Native save complete and native read-only reopen succeeded in audit\comparison_SP_C_20261102_234320, exit0.
- Deliberately stopped after73 steps: anomalous turbulence persisted. This is a recoverable diagnostic, NOT an approved result. Do not automatically extend this rejected diagnostic.
- Final full-plane audit: 361532 cells, 252161 active, 106812 inactive, 2559 acceptors, zero errors/difficult interpolation. All acceptors distance weighted.

Preserved inner40 source:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_inner40_20261102_223940\checkpoint.sim
Time .5184 s; 650472777 bytes.
SHA256 c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9.
Read-back forces/time matched source history. Also unapproved.

Older .3024 s checkpoint:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_resume_20261102_221053\error_checkpoint.sim
SHA256 266c78b674866e132ac61592ecce67470051376b8b010303611eb5841a45cae9.

Installed FullMeshViewRepresentation.isEmpty() always returns true; do not use it as a validity guard. Native saved fields may be readable even when isInitialized() initially returns false. Verify fields/time, do not reset or initialize a solved checkpoint.

''' +txt[b:]
a=txt.index('If Windows interrupted the flow run');b=txt.index('## Scientific hold',a)
txt=txt[:a]+r'''If Windows interrupted the current STEADY initializer:
1. Inspect the latest completed steady_iter_N.sim or steady_checkpoint.sim and its matching steady_iterations.csv, native save message, hash and timestamp.
2. Do not rerun FreshC0DistanceInit.java on this checkpoint: that macro intentionally accepts ONLY the original fresh mesh.
3. Continue the saved steady fields through a dedicated reviewed continuation macro or STAR GUI Run after opening that checkpoint, preserving Steady/SST/DISTANCE/flux correction/0 degrees. Do not initialize, clear solution/history, regenerate mesh or convert to transient before Work review.
4. Use the same CPU/MPI/license settings; continue the existing numerical solution. Record the starting iteration and compare loaded forces against the matching saved CSV row before running.

For any interrupted transient diagnostic, C0DistanceInterpolationTest.java can verify the saved time and Fx/Fz/Mh/CL/CD from history.csv and continue existing DISTANCE fields at dt=.002,40 inner,angle0. A documented scientific decision is required first because the last distance diagnostic was rejected. Never automatically restart a rejected experiment merely because a checkpoint exists.

''' +txt[b:]
txt=txt.replace('The approved next diagnostic is distance-weighted interpolation on the same saved mesh.','Distance interpolation alone also failed: omega-floor cells increased to1368 by step50 and the force discrepancy remained. The current approved diagnostic is clean initialization on the same pre-motion mesh with distance interpolation.')
txt=txt.replace('Updated: 2026-11-02,','Updated: 2026-11-03,')
doc.write_text(txt,encoding='utf8')
print('Updated current experiment/restart notes and startup checkpoint display; requested safe controller handover, STAR untouched.')
