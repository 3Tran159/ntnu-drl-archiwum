CORRECTED HYDROFOIL GEOMETRY - 29 October 2026

CURRENT CAD
HF_012_v3.prt: parametric NX 2606 part.
HF_012_v3.x_t: Parasolid 37.1 export for STAR/NX interchange.
HF_012_baseline_unmeshed.sim: STAR-CCM+ 2602 21.02.007 Double baseline; corrected foil active in the Boolean subtract operation. No volume mesh or solver run.

VERIFIED GEOMETRY
Root chord 1.190 m; full span 11.000 m; tip chord 0.3927 m.
Constant chord for |y| <= 2.750 m; taper ratio 0.33.
Zero nominal incidence, sweep, twist and dihedral.
Maximum root vertical thickness 142.774 mm (11.99785% chord).
Maximum vertical-midline camber approximately 2.5003% chord.
Full projected reference area 10.900868609 m2; half area 5.450434304 m2.
Full volume approximately 0.942312 m3.
Seven spanwise sections checked against the intended reconstructed 012 DAT.
Closed native and STAR tessellations; deviations at matched source points below 0.01 mm.
See geometry_verified.json for details and validation scope.

HISTORY
Original F:\ntnu\HF_v2.prt and HF_v2.x_t contain the 010 profile. They are unchanged.
All 1600 coordinate-expression formulas were checked against the old 010 DAT before replacement with 012 coordinates. Planform/pose master expressions and the NX feature construction were preserved.
The old 010 CAD stored inside the new STAR baseline is labelled ARCHIVE_010_INACTIVE and is excluded from the active subtract operation.
The baseline's legacy foil-wall boundary label may contain HF_v2, but its assigned surface is Subtract.HF_012_v3.Faces. The diagnostic meshed cases rename this wall HF_012_wall.
The overnight D001-D004 cases remain results for the old 010 geometry; do not relabel or normalize them with the new 012 area.

COMPLETED MESH-ONLY TRIALS
C001: 9,534,590 cells; C002: 6,037,861 cells; C003: 1,165,391 cells.
Current diagnostic candidate:
F:\ntnu\mesh_screening_20261028\coarse012_C003\HF_012_C003_mesh.sim
C003: zero negative-volume, unclosed or degenerated cells.
Any prism layers cover 100% of foil area; all 15 cover 94.559651%.
Minimum quality 5.0866e-5; minimum volume change 0.0110144; maximum skewness 84.9958 degrees.
Local review flags: 187 cells below quality 0.01; 283 above skewness 80 degrees.
Nominal prism settings retained: 15 layers, first height 0.1799 mm, total 15.46 mm.
C003 meshing time 19.2 s excludes startup, reports and file I/O.
All three cases have zero solver iterations. No new y+, forces, CL or CD are available.

NEXT CHECK
Review local prism collapse and quality flags; short hydrostatic startup at 0 m/s,
then an 18 m/s diagnostic run to measure runtime, CFL, wall y+ and force behavior.
Geometry verification is not hydrodynamic validation. The mesh is not approved
for production NWAR comparison; force/time/mesh sensitivity remain to be checked.
