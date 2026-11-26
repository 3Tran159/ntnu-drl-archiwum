# Local STAR inspection and API binding

Target: the user's ThinkPad, STAR-CCM+ 2602 / 21.02.007 / Double. The source `.sim` stays local. Drive is the deliverable destination, not the source of truth for the active model.

## Access and provenance

The online device THINKPAD-LUCJAN and source F:\ntnu\HF_mesh_v5.sim were identified and used. No file upload is required. Before remote execution, check any active STAR processes and avoid interfering with an ongoing solution. Work from a separate local directory and a verified copy. A `.sim` checksum alone does not cover linked external geometry or data files.

## Read-only installation evidence

- Exact executable path, file/build metadata, About text, double precision and machine/core configuration.
- Installation-local Java API documentation and relevant JARs. Record their version/hash where needed.
- Documented batch invocation, working-directory behavior, process lifetime and method of passing a job path to the macro.
- License availability and measured memory/disk resources. Do not assume the workbook's 12-million-cell value matches this machine.

Do not change installation settings, licensing configuration, running solver settings or device permissions merely to collect this information.

## Model inventory

Export a machine-readable inventory and readable report from the copied baseline. Record actual names/IDs/types, selections and definitions for:

| Group | Required facts |
|---|---|
| Geometry | Units, chord/span, full/half model, foil/LE/TE/tip surfaces, finite TE thickness, gaps, free-surface clearance, dependency file paths/hashes |
| Operations | All mesh operations in execution order, inputs/outputs, active meshers, existing mesh state, repair/wrapping/surface operations |
| Defaults | Base Size, surface target/minimum, curvature/proximity options, growth and transition options |
| Local controls | Surface and volumetric control selections, overlap/precedence, sizes, units, expression definitions and evaluated values |
| Prism | Distribution function and mode, near-wall/total thickness, N, stretching, relative/absolute units, reduction/retraction controls, near-core settings, local overrides, Enhanced Quality Prism option |
| Physics | Continuum assignments, SST variant, wall treatment, RANS/time model, VOF/wave definitions, material properties, gravity, boundaries, initialization and timestep |
| Reports | Report type, field function definition, selected regions/parts, units, cell versus face/area population, evaluation/refresh mechanism |
| Diagnostics | Existing scenes, sections, threshold parts, mesh logs, saved reports and quality locations |

The locked-settings JSON must be canonicalized consistently by the adapter and must cover geometry identity, physics, prism settings and non-varied controls. Its SHA-256 is not a substitute for reporting the readable values.

## Record and verify the adapter

1. On the working copy, record changing one real mesh control and restoring it. Inspect the generated Java classes, getters, options, quantity/unit calls and manager paths. Repeat for each proposed independent control.
2. Record/evaluate the necessary reports and diagnostic exports. Verify metric definitions using the **installed** help, especially skewness versus skewness angle and layer-coverage availability.
3. Record one mesh-generation operation and one save to a new case-local filename. Inspect what the operation actually executes; do not blindly invoke every operation if CAD reconstruction changes geometry.
4. Implement `MeshCase.java` against these calls and the adapter contract. Keep the unverified legacy package outside the active macro directory.
5. Compile and test under 21.02.007. Validate absolute-unit readbacks, unchanged locked settings, fresh reports, no solver iterations, output paths and exception propagation. Capture full build/launch logs.
6. Run three cases with the controller. Compare before/after input values, actual local resolution and prism sections. Do not treat changing cell count alone as proof that the intended region changed correctly.
7. Exercise a safe failure (for example an invalid report binding detected before meshing) and restart. Preserve the failed record and ensure the next attempt starts from a clean copy. Validate the Windows timeout/process-tree handling locally before a long unattended batch.

The installed Java API and exact model names have now been inspected, the preparation macro executed, and the model-specific adapter compiled. Runtime status is in audit/validation_status.json and the measured records. The recorded-macro steps above are an alternative reproducibility route; this implementation used installed API documentation, compilation and direct runtime checks. Original workbooks and source simulation were not modified.
