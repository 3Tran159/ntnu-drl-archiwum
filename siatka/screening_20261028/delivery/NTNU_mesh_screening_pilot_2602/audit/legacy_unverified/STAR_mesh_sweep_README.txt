NTNU CFD MESH ADVISOR V2 | STAR-CCM+ 50-MESH CAMPAIGN
28 October 2026 | Draft for local validation, not yet tested on your STAR installation.

FILES
- MeshSweep50.java             STAR-CCM+ macro, MESH ONLY (fixed prism stack; target y+~55)
- mesh_sweep_50.csv           50 cases derived from workbook starting values
- NTNU_CFD_Mesh_Advisor_y55_final.xlsx   Excel workbook separately on Google Drive

REQUIRED IN YOUR EXISTING STAR-CCM+ MODEL
1. Save a COPY of your working .sim as baseline_mesh_only.sim, not your ongoing solution.
2. Stop the ongoing CFD calculation; preferably prepare a model without solved fields.
3. Create five scalar GLOBAL PARAMETERS, with dimension Length (m), EXACT names:
     Mesh_Base, Mesh_Foil, Mesh_Wake, Mesh_VOF, Mesh_LE
4. Link each parameter via an expression to the actual relevant mesh control:
     Mesh_Base   > absolute Base Size
     Mesh_Foil   > foil surface target size
     Mesh_Wake   > local wake volumetric refinement
     Mesh_VOF    > local free-surface/interfacial volumetric refinement
     Mesh_LE     > leading-edge local surface target (absolute length)
   IMPORTANT: do not enter metre values in a STAR setting expecting percentages
   of Base Size. Use absolute-length settings or an expression converting units.
5. Keep the ENTIRE prism stack constant: first thickness, number of layers, total thickness and growth ratio. Baseline target y+≈55 as reported for Godø.
6. Create Reports on the appropriate fluid-volume cells with these EXACT names:
     Batch_CellCount           cell count
     Batch_MinVolumeChange     minimum Volume Change
     Batch_MinCellQuality      minimum Cell Quality
     Batch_MaxSkewness         maximum Cell Skewness Angle [degrees]
   Optional: Batch_PrismCoverage  coverage percentage (must be a user-designed report).
   If a report is missing or the reported values are invalid, do not rank the mesh.

FIRST RUN: THREE-CASE SMOKE TEST
1. Place the .sim, .java and CSV in a local work directory.
2. In MeshSweep50.java, leave CASE_LIMIT = 3.
3. Start the macro from STAR-CCM+ (Tools > Macro > Play) or use your version's
   documented command-line syntax, commonly:
        starccm+ -batch MeshSweep50.java baseline_mesh_only.sim
4. Inspect mesh_results.csv next to mesh_sweep_50.csv.
5. Check that cell count / quality vary as expected and that foil/wake/VOF/LE
   refinements actually change the mesh; compare mesh scenes for 3 cases.
   A parameter that is not linked to the corresponding mesh control does nothing.
6. Check runtime, memory, prism collapse and free-surface cell distribution.
7. ONLY THEN change CASE_LIMIT = 50 for the 50-case run.

OUTPUT AND SAFETY
- Generates 3 volume meshes by default (not 50). Does NOT run the CFD solver.
- Does NOT save any .sim snapshots. Results are append-written line-by-line
  into mesh_results.csv. The CSV is overwritten on each NEW macro execution.
- The results file has columns:
  case_id,status,cells,min_volume_change,min_cell_quality,max_skew_deg,
  prism_coverage_pct,mesh_time_s,file_mb,notes
- Missing optional coverage/size metrics are EMPTY, never made-up zeros.
- Stop after 3 consecutive errors, 10h elapsed between completed meshes, or
  first mesh whose reported cell count exceeds 12 million. In-process generation
  has no guaranteed timeout: a stalled mesher can still require manual stop.
- Never run on your only .sim copy, and never in parallel with the CFD solver.
- Required Reports are read only after generating a mesh. Make sure they are
  defined on the meshed region and actually evaluate the CURRENT mesh.
- Copy output columns status through file_mb (B:I of CSV) to workbook
  Mesh Results!B6:I55; the workbook contains case IDs in A6:A55 already.
  Check the case order and map notes into M if useful.
- Excel tab "Macro CSV" contains live formula-linked values. After modifying
  the workbook, export that tab's A1:F51 as values-only CSV and replace
  mesh_sweep_50.csv, or else macro will use the ORIGINAL default cases.

SCIENTIFIC METHOD
The 50 meshes are a DOEs for mesh-quality / cost screening, NOT a 50-point
mesh-convergence study. Once stable quality candidates are found, select
3 or more systematically refined grids for CL, CD and wave-elevation
sensitivity; also check time-step sensitivity and VOF-wave resolution.

COMPATIBILITY
STAR-CCM+ release and your .sim were not available for an end-to-end test.
Confirm API/macros with STAR's Tools > Macro > Record / Help > Java API.
A few calls or report definitions may need adjustment for your installed release.

LOW y+ TRIAL (SEPARATE STUDY)
Original calculator target y+=55 with N=15. A rough flat-plate estimate is h1≈0.180 mm.
At target y+=1, estimate h1≈0.00327 mm. Keeping the same target T≈15.46 mm
with baseline r≈1.221 requires ~35 layers, not 15. Validate feasibility separately.
All-y+ / High-y+ / Low-y+ wall-treatment configuration must be checked in STAR.

IMPORTANT: Macro CSV header is case_id,base_m,foil_m,wake_m,vof_m,le_m.
CSV is a snapshot of the current workbook defaults. If you edit the workbook,
export the tab Macro CSV as values-only CSV before rerunning the macro.
