> Campaign resumed by explicit user instruction on 2026-11-02. The pause/checkpoint details below are historical. Consult CAMPAIGN_STATUS.json for current work. W04 remains unauthorized for this task.

# HOME RESUME INSTRUCTIONS

**PAUSED. Wait for the user's explicit instruction in this same Work conversation.**
Recorded: 2026-11-02T16:19:26.084090+01:00. Nothing is scheduled to resume automatically.

## Checkpoint and exact saved state

Checkpoint:
    F:\ntnu\flap_control\checkpoints\Flap_CFD_HOME_RESUME_20261102.sim

STAR-CCM+ 2606.0002, build 21.04.009-R8. Saved time **0.260000 s**, timestep **0.002000 s**, step **130**, iteration **1040**. Mesh: **44,763 cells**, quasi-2D, 0.02 m span, Overset. The home checkpoint is an exact copy of the completed PoC. Its mesh and solution were not reset or regenerated.

SHA-256:
    3c32632e41c8e14f04dfde542abf7195e03a354c7c8886abf6566d087499ab29

Original last working checkpoint is preserved:
    F:\ntnu\flap_control\flap_poc_2606_20261102\FlapPOC_2606_working.sim

This completed mechanics PoC used U = 1 m/s, rho = 1000 kg/mÂ³, mu = 0.001 Pa s, Re = 1.19e6 based on c = 1.19 m, and a **laminar** single-phase model. Its rounded-nose radial clearance is 17.854 mm. Hinge origin is approximately x = 0.95183764 m, y = 0, z = 0.0212927324 m, axis +y. Motion law: delta = 5 deg sin(2 pi t/0.2 s). Saved delta is +4.7553 deg. The coarse-mesh forces are not hydrodynamically validated.

## First actions at home

1. Reconnect to this chat and explicitly instruct the agent to resume.
2. Audit competing STAR/MPI jobs before launching anything.
3. For safe read-only review, double-click:
       F:\ntnu\flap_control\checkpoints\OPEN_HOME_CHECKPOINT_READONLY.cmd
4. For editable continuation, copy the home checkpoint to a NEW filename, for example:
       F:\ntnu\flap_control\home_continuation\Flap_HOME_continuation.sim
5. Open that copy using STAR-CCM+ 2606, **4 CPU processes, Microsoft MPI (ms), CPU only**. Reuse the existing configured license profile. Equivalent PowerShell command, after making the copy:

       & 'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe' -np 4 -mpi ms -cpubind off -power 'F:\ntnu\flap_control\home_continuation\Flap_HOME_continuation.sim'

This opens saved state; it does not run automatically. Confirm time 0.26 s, dt 0.002 s, 44,763 cells, reports, scenes and motion. Do NOT initialize, clear the solution or regenerate the mesh. The saved PoC has a maximum physical time stop of 0.4 s if deliberately continued, but the PoC experiment is already complete.

The project launchers reject jobs while this marker exists:
    F:\ntnu\flap_control\PAUSED_FOR_HOME.json

Remove that marker only after an explicit user resume instruction and a fresh process audit. Do not run TestFlapPOC.java, RecoverFlapPOC.java or construction scripts to resume a solution: they were build/test tools and can initialize or remesh.

## Completed and pending work

Completed:
- PoC: 100 motion-only steps covering both +/-5 deg extremes, then 30 physical steps / 0.06 s calm transient. Native STAR frames, forces, moment and mesh diagnostics saved.
- Migration from C to F:\ntnu\flap_control, with original file hashes verified and C source directories removed.
- Read-only C01 audit: CL_hydro = 0.31565950495122014 and CD = 0.007002316911710474. Keep C01 as VOF reference; never change it or force single-phase results to match it.
- C01 saved t = 4.6992 s checkpoint has minimum absolute foil pressure approximately 34,323.895 Pa at [0.7172865, 0.02, 0.0953595] m. This is pressure screening of a checkpoint, not cavitation-model validation.
- New 2.5 mm gap geometry from all 575 native contour points. Collision sweep every 0.1 deg over +/-5 deg passed; minimum separation 2.49717 mm. **Not yet meshed or solved.**

Pending, in this order:
1. SP-A: original intact profile on C01's mesh in target single-phase physics.
2. SP-B: split geometry, flap fixed at 0 deg, without Overset.
3. SP-C: the same split geometry at 0 deg using the proven Overset architecture.
4. SP-A/SP-B isolates geometry, SP-B/SP-C the Overset numerical effect, SP-A/C01 the VOF bridge. Account for numerical uncertainty; do not expand into a full extra-variant campaign before these controls pass.
5. Mesh/gap/prism/connectivity and timestep checks; then static/dynamic studies only when the stationary model and safety checks pass.

**There was no interrupted 18 m/s solve.** The hydrodynamic stage had only reached geometry/configuration/API preparation. Its next step is model preparation, not pretending the PoC is an 18 m/s URANS checkpoint. No waves, DRL or surrogate training has started.

## Absolute paths for development and datasets

- Project root: F:\ntnu\flap_control
- Completed PoC: F:\ntnu\flap_control\flap_poc_2606_20261102
- Report: F:\ntnu\flap_control\flap_poc_2606_20261102\REPORT_PL.html
- Force/moment history: F:\ntnu\flap_control\flap_poc_2606_20261102\runs\transient.csv
- Angle/mesh history: F:\ntnu\flap_control\flap_poc_2606_20261102\runs\motion_check.csv
- Prescribed angle/rate history: F:\ntnu\flap_control\checkpoints\POC_prescribed_motion_history.csv (analytic derivative of the saved motion law; not a new simulation).
- Native frames and GIF: F:\ntnu\flap_control\flap_poc_2606_20261102\visualization
- New-stage protected seed: F:\ntnu\flap_control\hydro_validation_2606_20261102\reference\POC_working_protected.sim
- New-stage configuration: F:\ntnu\flap_control\hydro_validation_2606_20261102\config.json
- New geometry: F:\ntnu\flap_control\hydro_validation_2606_20261102\geometry\gap_002500um
- Geometry metadata: F:\ntnu\flap_control\hydro_validation_2606_20261102\geometry\current_geometry.json
- Full native contour source: F:\ntnu\flap_control\flap_poc_2606_20261102\audit\profile_vertices.json
- Java macros: F:\ntnu\flap_control\hydro_validation_2606_20261102\macros
- Python tools: F:\ntnu\flap_control\hydro_validation_2606_20261102\tools
- API inventory / reference audit: F:\ntnu\flap_control\hydro_validation_2606_20261102\audit
- Proven directed-mesh recipe, read only: F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\SetupQ2D.java
- Earlier preparation: F:\ntnu\flap_control\flap_drl_20261102
- Migration evidence: F:\ntnu\flap_control\_migration
- Machine-readable pause status: F:\ntnu\flap_control\CAMPAIGN_PAUSE_STATUS.json

## Agreed physics and limits

Target U = 18 m/s, rho = 1000 kg/mÂ³, mu = 0.001 Pa s, Re = 2.142e7, URANS SST k-omega, quasi-2D, initially single-phase/no waves. Reuse rigid rotation and Overset, with a smaller parametric hinge gap.

User confirmed 20 deg C and 10,000 Pa safety margin. IAPWS-IF97 region 4 gives vapor pressure 2339.214767 Pa, so the required absolute pressure threshold is 12339.214767 Pa. The future model must monitor minima and their collocated positions at every physical timestep on fixed foil, flap, gap and nearby liquid. A new per-timestep pressure dataset does not yet exist.

C01 has p_ref = 101325 Pa, reference altitude [0,0,2] m, reference density 0 and gravity [0,0,-9.81000042] m/sÂ². Its native AbsolutePressure field was checked. Its CL uses a hydrodynamic lift correction; preserve the distinction between total force and buoyancy-corrected force.

Free-surface clearance is independent. Virtual mean surface z = 2 m is inherited from C01; no universal safe h/c threshold is approved. Single-phase calculations cannot certify ventilation or local surface deformation. VOF immersion sensitivity remains pending for later work.

## Dependencies and known issues

The PoC checkpoint contains its own mesh, solution, reports, monitors, motion and scene. No PoC .simh was generated. CSV/PNG/GIF data, geometry and macros are preserved beside it. Installed STAR, JDK and Python runtime locations remain unchanged.

The archived C01 reference copy has an already-missing optional historical HF_foil.simh link. STAR warned about it during read-only inspection; the C01 .sim mesh and fields loaded. That history file is not a dependency of the fresh PoC checkpoint.

Earlier PoC surface-centroid angle checks stopped safely because active Overset surfaces were unsuitable position markers. Their partial logs are retained. The accepted motion check used solver-side rigid transformation and native mesh frames. Deprecated-API warnings exist; the accepted PoC finished normally.

Shutdown audit and readback evidence are in the checkpoints folder. Leave C01/W01/W03, all other agents' jobs and queues untouched. The user performs Windows shutdown.

Read-only verification note: the checkpoint loaded and passed its time, timestep, mesh and saved-report checks. STAR blocked its inherited AutoSaveBatch request on read-only close; exit code was 0 and the checkpoint hash remained unchanged. The earlier diagnostic report-recalculation attempt was also blocked by read-only mode and is archived separately.


## Final shutdown check

Native read-only checkpoint reload succeeded without advancing time or changing the solution. All STAR/MPI processes were absent in two audits separated by 5 seconds; project outputs were stable. Other PRE W04 state was paused. Original PoC and C01 hashes still match. No Windows shutdown was executed. The project remains paused awaiting the user.
