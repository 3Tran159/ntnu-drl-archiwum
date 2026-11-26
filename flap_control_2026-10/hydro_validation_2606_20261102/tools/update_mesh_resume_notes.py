from pathlib import Path
import datetime
h=Path(__file__).resolve().parents[1];p=h.parent/'HOME_RESUME_INSTRUCTIONS.md';s=p.read_text(encoding='utf8')
a=s.index('## Current experiment');b=s.index('## Latest preserved transient checkpoint',a)
s=s[:a]+r'''## Current experiment — 2026-11-03 00:16
Mesh-only diagnostic: PrepareC0OverlapRefinement.java, launch20261103_001516.
Output:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\c0_overlap1mm_20261103_001516
Protected uninitialized input:
F:\ntnu\flap_control\hydro_validation_2606_20261102\cases\SP_C_split0_overset\SP_C_build_error_20261102_191807.sim
SHA256 6a11e2692864a74e03c198cc90f3fc9cfb4c10ec7e3ba69fbdcf50c9e30ea2d4.

Only the Overset source mesh target changes to1mm in x[.70,.955],z[-.10,.15]m. Existing finer hinge control remains. Physical geometry, gap2.5mm, hinge/span/cage and background source mesh are unchanged. LinearQuasi2D interpolation matches the original C0 control.
No flow iterations or physical-time advance. Resource cap750000 cells and8 MPI CPU ranks. Before flow, require native full connectivity audit AND work_mesh_review.json showing background mesh identity. Do not treat mesh-prepared status as hydrodynamic approval.

Cold-start diagnostics, all preserved and unapproved:
- c0_distance_fresh_20261103_000031: CI enabled, DISTANCE, flux correction; diverged at40 iterations; initialization_error.sim saved.
- c0_fresh_noci_20261103_000523: same but continuity initialization disabled; diverged at50; initialization_error.sim saved.
- c0_fresh_noflux_20261103_001005: also disabled flux correction; tighter pressure guard stopped at10. Inconclusive about eventual convergence; do not claim flux correction was excluded.
All these are separate steady initializations at physical time0, not resets of the .6644s transient checkpoint.
The historical C0 already had uniform initial k/omega before its first steady solution, and its turbulence floor issue arose during solving. Fresh startup tests did not establish a sound alternative solution.

Next decision: review the local overlap mesh and donor size distribution, then initialize the candidate in a separate directory with explicitly documented numerical settings. No deflections, waves, W04 or DRL.

''' +s[b:]
p.write_text(s,encoding='utf8')
print('HOME_RESUME current phase updated; previous transient checkpoint preserved.')
