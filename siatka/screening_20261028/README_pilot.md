# NTNU hydrofoil mesh screening — workstation pilot

The inspected source is `F:\ntnu\HF_mesh_v5.sim`, saved in **Simcenter STAR-CCM+ 2602 / 21.02.007 / double precision**. The original file and the two Excel workbooks remain unchanged. `audit/technical_report.md` records the model, dependencies and findings. See `audit/validation_status.json` and `results/` for the final execution status; compilation alone is not a successful mesh test.

## Pilot result

| Case | Foil target [mm] | Cells | Mesh time [min] | Low-quality cells | Full 15-layer area |
|---|---:|---:|---:|---:|---:|
| A001 | 6.400 | 25,188,874 | 4.493 | 115 | 97.158% |
| A002 | 9.051 | 25,317,631 | 4.221 | 132 | 97.212% |
| A003 | 12.800 | 25,452,235 | 4.017 | 158 | 97.299% |

The authoritative comparison contains three completed meshes with fixed prism/physics settings and no CFD iterations. Coarsening the foil target increased cell count and low-quality-cell count, while the same minimum-quality location persisted. Keep A001 as the diagnostic reference. The one-axis sweep is stopped; a broad LHS is not justified by these observations. Prism/core-transition and local-resolution approval remains pending, so none is marked ready for CFD.

Open `results/dashboard.html` for the interactive table/plot, `results/pilot_comparison.png` for the overview, and `audit/technical_report.md` for the measured interpretation and next steps. The 6.4/9.05/12.8 mm targets correspond to 25.189/25.318/25.452 million cells, with 115/132/158 cells below quality 0.01. The original simulation checksum was verified unchanged after all work; the temporary 18.5 GB source copy was removed, while the clean baseline and saved cases were retained.

## Files and verified scope

- `star/InspectAndPrepare.java`: executed on a checksum-verified disposable copy; exported the actual model inventory and saved a clean 2.73 MiB baseline.
- `star/MeshCase.java`: model-specific macro using the installed API. Only the `HF_surface` target size is varied. Geometry, physics, base size, curve controls, volume refinements and prism settings are fixed and read back.
- `config/initial_doe.csv`: three pilot targets, 6.4, 9.0509668 and 12.8 mm. This is an automation/sensitivity pilot, not a grid-convergence sequence.
- `meshflow.py`: sequential launcher, fresh copies, hashes, isolated attempts, restart, timeout, license-key redaction, summaries and conservative quality classification.
- `config/campaign.json`: configured for the authorized ThinkPad paths and saved license configuration `bs`. It contains no license key.
- `results/dashboard.html`, `summary.csv`, `results.json`: measured campaign records only. Synthetic software fixtures stay in `tests/`.
- `audit/workstation/`: model inventory, baseline identity, API/build and launch evidence, and available runtime logs.

The first executable scope is one independent parameter. Base Size is fixed at 0.8192 m because multiple settings are relative to it. First prism thickness is 0.1799 mm; total thickness 15.46 mm; count 15; wall-thickness mode with geometric progression. Enhanced Prism Layers remains disabled. The user-requested y+≈55 remains a design target; achieved y+ cannot be measured without CFD.

## Workstation execution

The working directory is `F:\ntnu\mesh_screening_20261028`. It has a flat deployment (`MeshCase.java`, `campaign.json`, `initial_doe.csv`, `meshflow.py`) while this deliverable groups source/config/evidence in subdirectories. Commands below refer to the existing flat workstation deployment. The bundled Python is:

```text
E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\python\python.exe
```

From a PowerShell terminal in the working directory, use that executable in place of `python` if Python is not on PATH:

```text
python meshflow.py --config campaign.json check
python meshflow.py --config campaign.json run --cases initial_doe.csv --out pilot_v3 --limit 3
python meshflow.py --config campaign.json summarize --runs pilot_v3 --out results
```

Check the final validation record for the actual current campaign directory; revision-specific directories preserve failed integration attempts. Do not reuse a campaign directory after changing code, baseline, parameters or configuration: its identity check deliberately refuses that operation. Updating the macro requires updating its SHA-256 and API evidence.

Repeat the same run command to continue unattempted cases; successful cases are skipped. Failed/interrupted cases are skipped unless `--retry` is supplied. Retry adds a new attempt and keeps prior evidence. Do not manually edit measured outputs to make them pass. A STAR exit code of zero without a valid measurement is recorded as a failed attempt, because STAR can catch macro exceptions and still return zero.

Every attempt contains a fresh `baseline_copy.sim`, an adapter copy, `job.json`, a redacted `star.log`, and terminal `record.json`. Successful attempts additionally contain `measurement.json`, frozen-setting snapshots, reports and a saved `mesh.sim`. XYZ diagnostics are exported when a threshold population is nonempty and no larger than 100,000 cells. Missing diagnostics are recorded rather than replaced with zero.

Create a file named `STOP` in the campaign directory to stop before the next case. Ctrl+C terminates the current process tree. After a host crash, inspect the owned processes before removing a stale `.running` directory. Do not delete an active lock. Windows timeout and restart paths have been exercised with synthetic subprocess fixtures.

## Limits and interpretation

A process has a 1,800 s limit, including startup and export. The campaign invocation has a 5,400 s limit, a 15 GiB free-disk reserve and a 35M-cell post-generation cap. Cell count is checked after generation and cannot prevent meshing-time memory exhaustion. Runtime observations and saved file sizes should determine any larger budget. Completed case files are retained, not automatically deleted.

Negative-volume, unclosed-cell and degenerated-FE occurrences are extracted from STAR's mesh report; their sum is not a deduplicated defective-cell count, but zero means all three counts are zero. Scalar report values and diagnostic populations have explicit field names and scopes in the case notes. The threshold values used for local export are review triggers, not universal quality acceptance rules.

Measured prism coverage and the baseline reduced-layer map are included. Section verification, core transition and hydrodynamic resolution still require review. Pending prism/local reviews prevent a case from being accepted or placed on the eligible Pareto front, even when global metrics look good. No full CFD solver iterations are requested. The baseline's velocity configuration also needs review before CFD: the Calm wave has zero current/wind and supplies inlet velocity, whereas the workbook uses an 18 m/s example.

The delivered hashed pilot review records decision "stop", so the larger DoE remains gated. A future release requires a justified "proceed" review of completed pilot records, all parameter bindings and restart/failure evidence. Do not automatically spend a 12-case LHS budget on a single parameter. Inspect surface/control response, local quality, meshing cost and dyadic refinement effects first. Subsequent wake/free-surface axes must be bound and validated separately. DoE meshes must not be labelled a formal grid-convergence series.

## Software tests

```text
python -m unittest discover -s tests -v
```

These are synthetic controller tests, separate from real STAR pilot evidence. The package retains audit copies of the legacy macro and CSV as unverified source material. Neither that macro nor its workbook-derived settings is used as the active adapter.
