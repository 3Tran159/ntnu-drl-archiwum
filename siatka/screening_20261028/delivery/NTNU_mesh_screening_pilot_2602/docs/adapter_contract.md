# STAR adapter contract, schema version 1

This is the integration specification for the model-specific `star/MeshCase.java`. The installed 21.02.007 API has been inspected and the macro compiled. Real execution status is tracked separately in the campaign records. The current validated binding scope is one surface-target parameter; later axes require additional inspection and pilot evidence.

## Input

The process environment variable `NTNU_MESH_JOB` contains an absolute UTF-8 JSON path. The controller supplies:

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1 |
| `case_id`, `run_id`, `stage` | Exact case/attempt identity |
| `baseline_sha256` | Hash of the unchanged source `.sim` and each fresh copy |
| `parameters_m` | Object of approved variable names and absolute target values in metres |
| `locked_settings_sha256` | Expected canonical geometry/physics/prism/non-varied-control signature |
| `result_path` | Absolute case-local `measurement.json` path |
| `save_sim_path` | Absolute case-local `mesh.sim` path |

The STAR command loads the case-local `baseline_copy.sim`. The macro must check the actual loaded model identity and settings before changing it. Unknown parameters, ambiguous selections, invalid unit mappings or missing input objects must stop the attempt before mesh generation. Do not create arbitrary named parts/reports to hide a binding failure.

## Operation order

1. Check exact version/precision, job schema and loaded model identity.
2. Check locked settings, including all local prism overrides. Compare a readable snapshot plus its canonical hash.
3. Apply only the approved target controls, converting metres to the verified absolute/percentage expressions if necessary.
4. Read back **effective mesh controls**, not just free-standing global parameters, in metres. Save `readback_before_mesh`.
5. Generate a fresh surface/volume mesh using the verified operation sequence. Do not initialize or iterate the CFD solver. If an existing mesh must be cleared, use the recorded release-compatible operation and confirm it clears only the working copy.
6. Re-read control/locked settings. Evaluate fresh reports on the correct populations. Missing or undefined metrics stay absent; do not substitute zero.
7. Export local cell coordinates/threshold diagnostics, sections/scenes and prism evidence. Record provenance for every report/field and selection. Save the case snapshot to `save_sim_path` for the pilot and selected cases, with save status recorded. A failed save is explicitly reported.
8. Write the measurement JSON atomically only after generation/export finishes. On failure, emit a clear log and propagate the failure. A zero process exit without valid output is a controller failure, not success.

## Required output fields

- All exact identity fields: `schema_version`, `case_id`, `run_id`, `baseline_sha256`.
- `evidence_kind: "measured"`, `solver_version: "21.02.007"`, `precision: "double"`.
- `generation_status: "completed"` only on completed meshing.
- `solver_iterations_executed: 0` only when verified.
- `readback_before_mesh` and `readback_after_mesh`, each containing `parameters_m` and `locked_settings_sha256`.
- `metrics`: numerical scalar results. Required generation metrics: `cell_count` (positive integer) and `mesh_time_s` (positive measured duration). Hard-quality completeness also needs `invalid_cells` and `min_cell_volume_m3`, plus every configured rule.
- `reviews`: objects named `prism_review` and `local_resolution_review`, each with `status: "pass" | "fail" | "pending"` and an `evidence` reference. Pending/absent evidence prevents acceptance. Review assertions must come from inspected diagnostics; the controller cannot establish scientific truth from a string.
- Recommended additional metadata: actual build string, hardware/core count, operation names, report definitions/scopes/units, diagnostics paths/hashes, saved-model path/hash, save status and reason, notes, peak-memory value/method if available.

The controller adds `contract_status`, process elapsed time, case fingerprint, attempt directory and quality classification. An adapter must not write those controller-owned fields. The controller does not yet automatically validate every supplemental diagnostic file or authorize a candidate based on them; those remain part of the technical review.

## Configuration parameter format

Each `parameters` item has `name`, `unit` (m), `baseline`, `lower`, `upper`, `binding` (actual object/control plus conversion), `bounds_basis` (inspection evidence) and `independent_verified` (true only after dependency checking). Unknowns are not filled from the workbook. A fixed control should remain in the locked inventory rather than becoming a zero-width sampling axis.

Each `quality_rules` item has `name`, `definition`, `scope`, `unit`, and a numerical `min` and/or `max`. Declare metrics and thresholds together. The measured output key must refer to that exact definition/population. `quality_rules_verified` is set only after checking them on the baseline. `objectives` declares each metric's `name` and `direction` (`min` or `max`).

## Pilot review record

The review JSON contains:

- `decision: "proceed"` to release a larger batch; `"stop"` never releases it even with completed pilot records.

- `baseline_sha256`, `locked_settings_sha256`, `adapter_sha256`.
- `all_parameter_bindings_verified: true` after checking every planned axis.
- `restart_and_failure_test_verified: true` after demonstrating isolation/restart and local process control.
- `pilot_results`: at least three `{path, sha256}` references to completed, contract-verified pilot records.
- Human-readable notes covering mesh changes, prism behavior, local resolution, thresholds, bounds and the decision to continue or revise.

Attach it to `campaign.json` as `pilot_review: {path, sha256}`. Merely setting booleans without evidence is not validation. A validated record with decision "proceed" releases the larger batch; a "stop" record keeps it gated. Neither decision claims CFD accuracy or automatically accepts the meshes. The delivered review is "stop".

## Current limitations

The current adapter records exposed geometry/physics/prism/control settings plus an immutable clean-baseline hash. It does not provide a complete geometric topology hash. The frozen signature intentionally excludes generated representation descriptions, triangle counts, simulation time/iteration and the varied target. Readback files allow direct comparison.

Area-weighted prism coverage is measured for all three cases, and a reduced-stack spatial map is available for A001. Section-based confirmation of the geometric detector, local hydrodynamic resolution and prism/core-transition approval remain incomplete. STAR/MPI memory is available as sampled working-set sums, not exact physical-memory peaks. These limitations cannot be resolved from global minima. Diagnostic XYZ tables use cell-centred extraction on threshold parts and have a 100,000-cell export cap. Available metric fields are enumerated per run; undefined reports remain absent. The controller does not approve scientific quality automatically.

STAR may return exit zero after a macro exception. The controller therefore requires a matching, complete measurement JSON and never equates exit zero with a generated mesh. `NTNU_MESH_PROBE=1` is a development check that returns before meshing and creates no measurement; it must be absent in production runs.
