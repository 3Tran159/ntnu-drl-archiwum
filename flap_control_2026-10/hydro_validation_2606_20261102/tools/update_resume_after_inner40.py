from pathlib import Path
import re,shutil
h=Path(__file__).resolve().parents[1];p=h.parent/'HOME_RESUME_INSTRUCTIONS.md'
backup=h/'audit/HOME_RESUME_before_distance_20261102_2317.md';assert not backup.exists();shutil.copy2(p,backup)
s=p.read_text(encoding='utf8')
a=r"""## Current experiment
C0DistanceInterpolationTest.java: static flap 0°, same native modified foil and 2.5 mm gap, 361532 cells, single-phase water, U=18 m/s, rho=1000 kg/m3, mu=.001 Pa s, Re=2.142e7, URANS SST, dt=.002 s, 40 inner iterations.
Only Overset interpolation is changed from LinearQuasi2D to distance weighted. The running source snapshot is immutable. No geometry, mesh, physical boundary condition, angle, saved field or physical-time reset.

Current launch: 20261102_231609; input time .5184 s. Read NIGHT_STATUS.json to distinguish STARTING from actual solving.
Output:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_distance_20261102_231609
Max 150 physical steps, unique checkpoints every 25; full field/residual exports every 25. No further job is scientifically approved automatically.
The previous launch 20261102_230957 stopped before any timestep because an early isInitialized flag was false. Its error copy/logs remain preserved. The corrected macro verifies saved time and Fx/Fz/Mh/CL/CD against the source history and contains no initializeSolution or clearSolution calls.

The inner40 control was deliberately concluded by Work after 108 steps / three stable windows; raw native status paused_by_marker and hydrodynamic_convergence_verified=false are preserved. Mean last25: CL=.3754542958, CD=.00647303370, Mh=-11.36768573 Nm. This does not explain the B/C force bias; it is a diagnostic conclusion, not model acceptance.

## Preserved source checkpoint
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_inner40_20261102_223940\checkpoint.sim
- Saved physical time .5184 s, dt=.002 s; 650472777 bytes.
- SHA256: c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9.
- Native save completed, hash verified, native exit0 and no remaining owned children before new launch.
- Full 361532-cell final audit: 0 errors, 0 difficult interpolation, positive volume/quality.
- Read saved_solution_readback.txt in the new output directory for evidence of native field/time re-read. A PID or saved-file hash alone is not solution-readback verification.
- Scientific acceptance remains false.

Older .3024 s checkpoint:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_resume_20261102_221053\error_checkpoint.sim
SHA256: 266c78b674866e132ac61592ecce67470051376b8b010303611eb5841a45cae9.
The installed FullMeshViewRepresentation.isEmpty method always returns true. Full Overset diagnostics must use an extracted midspan plane, not direct full-representation region reports/tables.

"""
s=re.sub(r'## Current experiment.*?(?=The older t=0.3004 s candidate)',lambda _:a,s,flags=re.S)
s=s.replace('Use C0InnerIterationTest.java only if continuing this specific iteration-sensitivity test.','Use the current C0DistanceInterpolationTest.java source for this diagnostic. It verifies saved time/forces against the source-directory history.csv, accepts an existing DISTANCE option without changing it, and keeps dt=.002, 40 inner, angle0. If its source option is LINEARQUASI2D it performs the explicitly recorded interpolation change. Never use it for nonzero angles.')
s=s.replace(' C0InnerIterationTest.java ',' C0DistanceInterpolationTest.java ')
s=s.replace('Evaluate the 40-iteration test against the original C0 histories before approving another diagnostic.','The 40-inner test changed CL by only about +.0235% and CD by -.0780% from original C, while differences from B remain +14.714%/-9.640%. Its stable force history does not make the anomalous local turbulence solution valid. The approved next diagnostic is distance-weighted interpolation on the same saved mesh.')
p.write_text(s,encoding='utf8');print(p)
