from pathlib import Path
import json
h=Path(__file__).resolve().parents[1];p=h.parent/'HOME_RESUME_INSTRUCTIONS.md';s=p.read_text(encoding='utf8')
a=s.index('## Current experiment');b=s.index('## Latest preserved transient checkpoint',a)
s=s[:a]+r'''## Current experiment — 2026-11-03 00:47
FreshC0RefinedInit.java: bounded steady numerical initialization on the mesh that passed native and Work checks. Read NIGHT_STATUS/NIGHT_QUEUE_STATE for the active run directory and latest checkpoint; do not infer progress from the controller PID.

Verified zero-step source:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_overlap_band05mm_20261103_003837\SP_C_mesh_ready.sim
SHA256 35b44cb5cd54d35cf7e7b849140524b9f2be5d4ffc8b583da44495db5ba88865.
579468 cells: BG304810, OV274658; active372961, inactive203063, acceptors3444.
Full native audit: zero Overset errors, zero difficult interpolation, all acceptors DISTANCE, positive volumes, minQ.0610482. Background cells match control uniquely, max center error2.85e-14m. Review file: same directory/work_mesh_review.json.

Geometry/physical conditions: original modified foil, gap2.5mm, hinge x/c.8, 0deg, span.02m, U18, rho1000, mu.001, Re2.142e7, SST. Only Overset source resolution changed: outer1mm plus inner0.5mm atx[.74,.955],z[-.08,.13]m. Existing hinge.35mm control retained; no physical geometry change.
Cell-size mismatch remains locally up to5.232; positive connectivity is not accuracy validation. Refinement moves the interpolation interface nearer the wall; near-wall field checks are required.

Current startup: steady mode, physical time0, DISTANCE, conservation NONE, continuity initialization enabled100 iterations. Checkpoints/fields/full audit every250 iterations, cap1500. CL/CD/Mh and pressure/mass windows checked; no scientific/training acceptance. Early numerical initialization is not a physical time history. Before any accepted comparison, restore FLUX_CORRECTION and matched URANS settings, then assess force stabilization, residuals, turbulence and pressure.

Earlier cold-starts on361532-cell mesh are preserved as rejected/inconclusive:
- c0_distance_fresh_20261103_000031: CI enabled/flux correction; divergence40iterations.
- c0_fresh_noci_20261103_000523: CI disabled/flux correction; divergence50iterations.
- c0_fresh_noflux_20261103_001005: CI and flux correction disabled; tighter pressure guard stopped10iterations; inconclusive about eventual convergence.
- 1mm and local0.5mm-patch mesh candidates were rejected for one difficult interpolation cell each. No flow was run on them.
None replaces the preserved .6644s transient diagnostic below.

Next: review new startup fields; only after a scientifically sound initial state continue matched URANS. No deflections until C0 bias explained and approved. No W04, waves or DRL.

''' +s[b:]
p.write_text(s,encoding='utf8');print('HOME_RESUME updated to the positively audited mesh and current initialization safeguards.')
