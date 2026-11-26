# Night campaign — 28/29 October 2026

Live dashboard on the workstation: `F:\ntnu\mesh_screening_20261028\dashboard.html`.
The dashboard embeds data directly and works from a local file. It reloads every 60 seconds; a local Python watcher rebuilds it every 30 seconds for 14 hours. Its Polish work log separates work performed, findings, problems and next steps. Mesh saves and CFD start/end/progress events are automatic. Timestamps display in Europe/Berlin.

## Decisions and observed evidence

- The original `F:\ntnu\HF_mesh_v5.sim` is not an output target. Meshing uses the clean copied baseline; CFD uses a separate copy of each saved mesh on E:.
- The user selected 18 m/s, calm water, and sequential runs. Water current and air velocity are both `[18, 0, 0]` in the foil frame. The existing first-order implicit unsteady scheme, SST/all-y+ treatment, time step `1e-5 s`, geometry and angle remain unchanged.
- Full 15-layer area improved from 97.158% in A001 to about 98.763% with legacy prisms and Near Core Layer Aspect Ratio 2. Raising that ratio to 4 added only about 0.002 percentage points and increased the number of cells with Cell Quality <0.01. The proposed 99.9% goal is not achieved.
- Enhanced Quality Prisms in B001 gave only 94.237% full-layer area and three cells with skewness angle >85°. It is excluded from the night candidates.
- Local A001 diagnostics show reduced/terminated stacks around the trailing edge and compression near the prism/core transition. The worst Cell Quality cell is in detected layer 15, but its skewness angle is only 19.934° and Volume Change is 0.13789. Only 2 of 115 cells with Q <0.01 also have skewness >80°. These metrics identify different defects.
- A real 25.19-million-cell, 8-worker CFD initialization exhausted RAM and was stopped before completing a solver step. Sequential execution alone does not solve that capacity problem. Coarsening only the HF_fine volume refinement produced the four smaller D cases below.
- The real 24-worker D001 test passed: two time steps, 40 inner iterations, physical time 2e-5 s, approximately 879 s solver wall time, and minimum 15.39 GiB free RAM. The sequential queue actually launched at 21:41 Europe/Berlin. The test is the launch gate. It must finish at least two time steps and retain at least 12 GiB free physical RAM. The supervisor records a blocked state if the gate fails; it does not silently treat initialization or exit code zero as success.
- The 12 GB GPU was not used: the installed GPU guide's approximate 2 GB per million cells for a simpler double-precision trimmed turbulence case suggests insufficient VRAM. This is a capacity estimate, not a measured GPU run or a claim that 2602 lacks VOF support.

## Four mesh candidates

All keep foil target 6.4 mm, curve target 3.2 mm, nominal first prism height 0.1799 mm, 15 layers and total prism thickness 15.46 mm. The HF_fine factors multiply all original x/y/z sizes. Other refinement controls are retained.

| Case | HF_fine x/y/z [mm] | Near Core AR | Cells | Q <0.01 cells | Full 15-layer area |
|---|---|---:|---:|---:|---:|
| D001 | 12.8 / 25.6 / 12.8 | 2 | 15,866,740 | 144 | 98.763% |
| D002 | 25.6 / 51.2 / 25.6 | 2 | 14,902,626 | 133 | 98.763% |
| D003 | 12.8 / 25.6 / 12.8 | 4 | 15,225,539 | 459 | 98.765% |
| D004 | 25.6 / 51.2 / 25.6 | 4 | 14,261,528 | 471 | 98.765% |

All four have zero reported negative-volume, unclosed and degenerate-FE cells, minimum Face Validity 1, maximum skewness below 85°, and minimum Volume Change above 0.011. These integrity checks do not confer mesh independence or hydrodynamic accuracy. The cases remain under review, so the dashboard does not mark them acceptable.

## Execution and recovery

`overnight_supervisor.py` waits for the probe, hashes the saved D meshes and then runs D001 → D002 → D003 → D004 with 24 CPU workers and a two-hour solver wall-time budget per case. Initialization/loading is additional. Each STAR process also has a hard timeout. Checkpoints are saved about every 15 minutes at time-step boundaries and at completion. An interrupted inner iteration can delay a graceful checkpoint.

Output directories: `E:\ntnu_cfd_night_20261028\D001` through `D004`. Each receives a fresh working copy, a frozen macro copy, runtime metadata, redacted `star.log`, `history.csv`, resource samples, `prepared.sim`, checkpoints and terminal status. The original mesh source SHA-256 is checked before every launch. Do not reuse a failed output directory; preserve it and choose a new attempt name.

The controller requires 40 GiB free RAM before a case, requests a graceful stop below 10 GiB, and terminates its owned case below 6 GiB. A memory stop or hard timeout stops the queue. The controller prevents sleep while the queue runs. The laptop must remain powered and Windows must remain running.

To stop the queue, create `E:\ntnu_cfd_night_20261028\STOP_ALL`. To stop one case gracefully, create `STOP` inside its output directory. These markers are checked between outer calls. To stop dashboard updates, create `F:\ntnu\mesh_screening_20261028\night_20261028\STOP_DASHBOARD`.

The final macro disables inherited automatic solution-history recording; `.sim` checkpoints and the CSV history provide the case-local evidence. It also attempts a final foil table with y+, pressure and prism geometry fields, plus locations of cells with convective CFL >5 when fewer than 100,000 such cells exist. This threshold is diagnostic, not a universal stability limit. An optional export failure is recorded separately from the solver result.

## Interpretation and limitations

The first D001 step took approximately 419 s of solver time for only `1e-5 s` of physical time. Its forces are dominated by startup, with maximum velocity about 52.9 m/s and maximum convective CFL about 16.44. These are not converged force results. The fixed small time step makes the overnight comparison primarily a test of startup behavior, solver robustness and computational cost. Compare runs at a shared physical time; equal wall-time budgets alone are not an accuracy comparison. A later operating-point/time-step and convergence study is required.

Layer counts come from STAR's geometric detection and full-stack coverage is weighted by foil area. Do not infer area coverage from unweighted CSV row counts. Nominal settings do not guarantee the achieved local layer thickness or y+. The wall table's PrismCellThickness is a geometric diagnostic, not the prescribed first-cell height.

Raw meshing notes contain a formatting error saying `SkewnessAngle < 80/85`; the implemented threshold is ABOVE and the named metric keys/counts are correct. Raw measurements were preserved. The legacy JSON key `parameters_m` also contains dimensionless HF_fine factors, aspect ratio and a Boolean; use field names for units.

The three A cases and B/D mesh measurements have zero solver steps at mesh-generation time. New CFD evidence is kept separately. Historical pilot reports under `audit/` describe the earlier mesh-only stage; this file and the live dashboard describe the night extension. After each case, `summarize_night.py` writes `nightly_summary.json` and `nightly_summary.md`, comparing available histories at a shared physical time and marking missing cases. The archived HTML is a snapshot, whereas the workstation HTML continues updating while its watcher runs.
