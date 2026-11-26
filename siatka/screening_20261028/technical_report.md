# Technical inspection report

NTNU hydrofoil project · 28 October 2026

## Outcome and evidence boundary

The local workstation is now accessible through Desktop Commander. The actual file `F:\ntnu\HF_mesh_v5.sim` was copied, both copies hashed, opened in the installed **2602 / 21.02.007 / R8 double** application, and inspected. The source was not modified. A 2,863,756-byte clean derivative was saved after clearing only the working copy's solution and generated representations. The original is 18,483,961,071 bytes.

The original model contained **25,188,874 cells**, iteration 52, physical time 0.00003 s. Its mesh report returned zero negative-volume cells, zero unclosed cells and zero degenerated FE cells. Face validity minimum was 1.0, volume-change minimum 0.01100059, maximum skewness angle 84.553012617 degrees. These are measurements of the pre-existing mesh, not results of the new pilot and not proof of local prism quality or CFD accuracy.

The initial default batch launch failed at license checkout. The user's existing saved server configuration `bs` successfully checked out `ccmppower` and completed preparation on eight processes. License keys are redacted before log persistence.

## Actual model and dependencies

| Setting | Inspected value | Treatment |
|---|---|---|
| Operations | Subtract; Automated Mesh | Preserve sequence and geometry |
| Mesher | Surface Remesher, Trimmed Cell, Automatic Surface Repair, Geometric Sensitivity, Prism Layer | Keep unchanged |
| Base Size | 0.8192 m | Fixed: many controls inherit percentages |
| Foil target / minimum | 0.0064 m / approximately 0.0004 m, both relative | Vary target only; keep minimum percentage and fixed base |
| Curve target / minimum | 0.0032 / 0.0016 m, absolute | Fixed; applies to observed edge selections, not assumed separate LE/TE controls |
| HF_fine x/y/z | 0.0064 / 0.0128 / 0.0064 m | Fixed |
| HF_coarse x/y/z | 0.1024 / 0.1024 / 0.1024 m | Fixed |
| HF_wake x/y/z | 0.2048 / 0.1024 / 0.1024 m | Fixed during pilot |
| free_surf x/y/z | 0.8192 / 0.8192 / 0.0256 m | Fixed during pilot |
| HF_wave x/y/z | 0.2048 / 0.4096 / 0.0256 m | Fixed during pilot |
| Prism definition | Geometric Progression; Wall Thickness | Growth determined by h1, N, total thickness |
| Prism h1 / N / total | 0.0001799 m / 15 / 0.01546 m absolute | Fixed, including local override flags |
| Enhanced Prism Layers | False | Fixed |
| Prism exception | bottom surface control disables prisms | Preserve existing setting |
| Core/prism size limit | Enabled; multiplier 2 | Fixed |
| Physics | SST k-omega, All y+ Wall Treatment, VOF, implicit unsteady | Fixed |
| Time step / temporal order | 0.00001 s / first order | Preserved; no solver steps run |

There are **no global parameters** in the inspected model, so the legacy macro's assumed Mesh_Base/Foil/Wake/VOF/LE bindings do not exist. Near-wall thickness is a full specified first layer thickness, not an achieved y+. For geometric progression, the fixed total and first thickness imply a nominal growth ratio near 1.221; local suppression/reduction can alter realized layer stacks and needs diagnostic inspection.

The baseline's Calm wave reports zero current and wind; inlet and initial velocity select Velocity of Calm. This differs from the workbook's 18 m/s example. Preserve it during mesh screening, but verify the intended physical operating condition before any CFD validation. No speed was changed.

## First executable pilot

The selected axis is the actual `Automated Mesh / HF_surface / Target Surface Size`. Three targets are 0.0064, sqrt(0.0064*0.0128), and 0.0128 m: the original, log midpoint, and one dyadic coarsening level. This bounded pilot avoids multiplying the existing 25M-cell budget through a global refinement. It is an automation/surface-control sensitivity pilot, not a grid-convergence sequence. The fixed HF_fine volume control and curvature can limit the response; an unchanged cell count would be informative evidence of that dependence, not a failed experiment.

Frozen configuration readbacks cover 1,169 exposed properties/class bindings, excluding the varied target and documented generated-state fields. Clean-copy hashes establish immutable input provenance; the property signature does not claim to be a complete CAD B-rep fingerprint. Configured maximums are 35M cells (checked after generation), 1,800 s per process including startup/export, 5,400 s per invocation, and a 15 GiB disk reserve. These are operator resource policies, not scientific quality thresholds.


## Workbook findings

The two workbooks were read through their stored OpenXML values/formulas and imported read-only with the spreadsheet inspection engine. Neither workbook was modified or exported. The primary calculator outputs agree to floating-point rounding. They are analytical estimates under their stated smooth turbulent flat-plate assumptions.

| Quantity | Stored value in the final advisor | Evidence |
|---|---:|---|
| Reference speed | 18 m/s | `Calculator!C6` |
| Reference length | 1.19 m | `Calculator!C7` |
| Target y+ | 55 | `Calculator!C10` |
| Number of prism layers | 15 | `Calculator!C11` |
| Estimated first full cell height | 0.179927 mm | `Calculator!G6:G7` |
| Ideal geometric growth ratio | 1.22100505 | `Calculator!G8` |
| Ideal total prism thickness | 15.458476 mm | `Calculator!G10:G11` |
| Ideal outermost layer | 2.945384 mm | `Calculator!G12` |
| Proposed base / foil / wake / VOF / LE targets | 0.119 / 0.0119 / 0.0238 / 0.01 / 0.002975 m | `Mesh Advisor!G6:G11`; legacy CSV M001 |

These quantities must not replace the actual model's settings. Target y+ is a design intention; achieved y+ requires a flow solution. The calculator distinguishes wall-centre distance from full first-cell height, with an ideal factor of two. Actual curved/skewed cells need local measurement.

### Confirmed issues affecting screening

1. **Incomplete quality acceptance.** `Mesh Results!J6` reads C6:F6 but not generation status B6 or prism coverage G6. `L6` can consequently label a row `PILOT CFD` using only that gate and the cell budget. A failed or incomplete row with otherwise filled metrics could be promoted. Neither formula checks invalid cells, minimum volume, face validity or local resolution. This is a formula-logic finding; no physical mesh was classified.
2. **Unvalidated thresholds.** `Mesh Results!C3=0.01`, `F3=0.00001`, `I3=85` and the 12-million-cell budget are editable screening assumptions. They are not installation-specific acceptance evidence or a hardware benchmark. They were not adopted as validated limits in the new controller.
3. **Directional CFL versus summed CFL.** `VOF Design!G15=MIN(G12:G14)` enforces individual directional estimates. With its stored inputs, it gives 0.000694444 s. The workbook's own summed orthogonal definition at that step gives `dt*(18/0.025 + 0.5/0.01)=0.534722`, above its target of 0.5. A corresponding two-direction sum estimate is `0.5/770=0.000649351 s`, before any tighter wave-period or solver-specific restriction. This is an internal analytical inconsistency, not evidence that the actual STAR timestep is unstable. Current stored dt=0.0001 s gives the displayed sum 0.077.
4. **Geometry is not established.** `Mesh Advisor!C7=11.9 m` explicitly calls the span an example. The project NX README gives an editable demonstration span of 11.0 m and says its dimensions are not a specific ferry reconstruction. Neither value establishes the `.sim` geometry.
5. **Documentation drift.** `Mesh Advisor!B30` calls LE/TE targets non-sweep variables, but the macro does vary LE. `Calculator!B43` still describes y+=1 as the default although C10 is 55. The `References` sheet correctly states that the Godø y+ attribution was reported by the user and needs verification.

## Legacy macro findings

Source: `STAR_mesh_sweep_y55_fixed_prism.zip`, containing `MeshSweep50.java`, `mesh_sweep_50.csv`, `STAR_mesh_sweep_README.txt`.

| Priority | Finding | Exact evidence / consequence |
|---|---|---|
| Critical | Results overwritten on restart | Java line 82 uses `new FileOutputStream(output)` without append; existing results are truncated before CSV validation |
| Critical | No clean reload between cases | One `getActiveSimulation()` instance; loop calls `generateVolumeMesh()` at line 135 without new baseline load |
| High | Parameter/report names are assumed | Lines 22–29 hardcode five global parameters and four reports; existence does not establish binding, units, scope or freshness |
| High | Prism preservation is not checked | Parameter assignments at line 133 have no before/after verification of relative thickness, local overrides or inherited dependencies |
| High | No saved candidate model | `SAVE_EACH_SIM` is reserved and saving is not implemented (lines 20 and 35–37) |
| High | Weak resource protection | Ten-hour limit is checked between cases; cell-count limit is checked after mesh generation; neither prevents in-process stalls or memory exhaustion |
| High | No formal restart identity | No baseline hash, adapter hash, exact build, case fingerprint, attempt identifier or resume ledger |
| High | No local diagnostics | Optional prism report may be absent; no location exports, face-validity assessment or first-height/layer-count verification |
| Medium | Incomplete output is not a failure streak | Line 161 resets the error counter even for `INCOMPLETE` reports |
| Medium | Trial inputs are fixed in advance | First three rows only vary Base Size from 0.119 to 0.08925 and 0.14875 m; no model evidence supports those bounds |
| Medium | Coarse input validation | Positive lengths up to 100 m are admitted independently; no model-specific bounds or coupled-control check |

The legacy package already acknowledges lack of a local test and avoids full CFD solves. Those are useful safeguards, but do not validate the API or configuration.

## Implementation and validation

`InspectAndPrepare.java` executed successfully in the installed application and exported 373 inventory nodes. `MeshCase.java` compiles against the installed Java API using bundled JDK 21.0.8. It validates the clean copy, checks fixed settings before/after parameter application and meshing, generates a single volume mesh, collects reports, saves the result, and exports an atomic measurement JSON. Runtime pilot status is recorded separately in `results/` and `audit/validation_status.json`.

The Python controller uses independent sequential STAR processes and fresh baseline copies, preserves attempts, checks identity and configuration hashes, redacts license keys, handles timeouts, and generates CSV/JSON summaries and a dashboard. Its software tests use explicitly synthetic fixtures, never campaign measurements. Local mesh diagnostics request XYZ cell tables where threshold populations are nonempty and at most 100,000 cells. Missing reports remain missing. Prism coverage, missing-layer distribution and hydrodynamic local resolution remain explicit reviews; pending reviews prevent acceptance and Pareto eligibility.

No full CFD solver iterations are requested. No claim of achieved y+, force accuracy, mesh convergence or time-step convergence is made. A larger DoE remains gated until three completed pilot records and the runtime review justify it. Given a single screened axis, a dense 12-point LHS is not automatically justified; the next stage should respond to measured sensitivity, mesher quantization and runtime cost.

## Measured pilot outcome

| Case | Foil target [mm] | Cells | Mesh time [min] | Cells with quality < 0.01 | Foil area with 15 detected layers |
|---|---:|---:|---:|---:|---:|
| A001 | 6.400 | 25,188,874 | 4.493 | 115 | 97.158% |
| A002 | 9.051 | 25,317,631 | 4.221 | 132 | 97.212% |
| A003 | 12.800 | 25,452,235 | 4.017 | 158 | 97.299% |

All three completed with zero negative-volume/unclosed/degenerated-cell occurrences, minimum face validity 1.0, unchanged frozen settings and zero solver iterations. They were saved separately. The original source checksum is unchanged. Two earlier calibration meshes are retained as audit history and excluded from this comparison because their extraction revision had a skewness-unit error.

From 6.4 to 12.8 mm, cell count increased **1.046%**, poor-cell count increased **37.39%**, and generation time decreased **10.59%**. Runtime is a single observation at each setting, not a statistically established performance difference. Minimum cell quality stayed approximately **1.05812e-5** at the same point **(0.120927, 4.250387, -0.013646) m**. All but one low-quality cell in each case was inside the fixed HF_fine box: 114/115, 131/132 and 157/158. A003 also introduced a VolumeChange < 0.01 point at **(0.710233, 4.954038, 0.000137) m**, with value 0.00396553; it remains above Siemens' 1e-5 suspect-value guidance.

Detected full-stack area coverage was 97.158–97.299%, while at-least-one-layer coverage was 100%. Detected first-layer thickness ranges were 0.1106–2.2413, 0.1082–2.2206 and 0.1036–2.1900 mm, versus the fixed nominal 0.1799 mm. These are geometric detector outputs and require section checks before every reduction is interpreted as a mesher failure. The baseline follow-up exported 347,807 reduced-stack wall samples. Spatial bins show two narrow edge bands, with the strongest detected reductions in the downstream band. The 799-bin portable summary is a projection, not an area-weighted coverage calculation.

The sampled sums of matching STAR/MPI working sets peaked at 14.21, 13.48 and 16.83 GiB. These are sampled process sums including diagnostic/export activity, not exact physical-memory peaks. Shared pages can be counted more than once.

**Adaptive decision: stop this one-axis sweep.** Retain A001 as the reference for targeted diagnostics; it has the fewest cells and fewest low-quality cells of this pilot. The same worst cell and edge-band prism reductions persist, so a 12-case surface-target LHS is not justified. No case is promoted to an approved CFD candidate and the eligible Pareto set remains empty while prism/core-transition and local-resolution review are unresolved. This does not mean the meshes cannot be used; it means adequacy has not been established by the collected screening evidence.

Next, inspect sections near y=0.5, 2.75, 4.25 and 5.4 m and verify the detector against the actual layer topology. Then consider a targeted change to the existing curve/local surface-core controls with the prism specification fixed. No new LE/TE object names or executable bounds are invented here. Before CFD, resolve the model's zero-current Calm/inlet velocity against the workbook's 18 m/s example. Separate spatial and timestep verification remain future phases.

Figures: `results/pilot_comparison.png`, `results/low_quality_locations.png`, `results/prism_reduction_locations.png`. Machine-readable results, raw scalar reports, diagnostic XYZ tables, method definitions and resource samples are included. Full saved .sim cases and the 30.4 MB prism-location CSV remain in the workstation working directory.

## References and provenance

- Source file metadata and hashes: `drive_sources.json`, `source_hashes.json`, `workbook_evidence.json` in this directory.
- Siemens, [What's new in Simcenter STAR-CCM+ 2602?](https://blogs.sw.siemens.com/simcenter/simcenter-star-ccm-2602-released/), published 24 February 2026. Supports existence of Enhanced Quality Prisms; does not verify this model's setting or Java calls.
- Siemens Xcelerator Academy, [Process Automation using JAVA](https://training.plm.automation.siemens.com/ilt/iltdescription.cfm?pID=TR09306_______STAR_2020.1_B7). Supports recording and maintaining version-dependent macros; not a 21.02.007 API reference.
- NASA Glenn, [Examining Spatial (Grid) Convergence](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html). Used for the distinction between grid screening and systematic refinement, observed order and asymptotic-range checks.

The original calculator and its established functionality are preserved. Reported issues remain findings, not silent workbook edits.
