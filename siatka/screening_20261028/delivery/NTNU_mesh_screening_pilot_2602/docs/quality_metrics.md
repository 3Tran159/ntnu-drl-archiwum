# Metric definitions and limits — installed 21.02.007

The source is the installed Siemens help under `E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\doc\en\online\STARCCMP`. Actual field names were also enumerated in the generated model. No metric name is taken solely from the legacy macro.

| Export | Field / population | Interpretation |
|---|---|---|
| Cell count | Volume Mesh FvRepresentation | Non-halo total reported by STAR |
| Mesh time | Monotonic clock around generateVolumeMesh | Excludes application startup and diagnostic/export time; process_elapsed_s includes them |
| Minimum cell volume | Volume, all fluid cells, m³ | Physical cell volume; a positive minimum does not ensure good shape |
| Minimum cell quality | CellQuality, all fluid cells | Dimensionless measure based on neighbouring cell-centre geometry and face orientation; 1 is ideal, near 0 approaches degeneration. Suitability depends on physics. The 0.01 threshold is a localization trigger, not universal rejection |
| Minimum face validity | FaceValidity, all fluid cells | Area-weighted outward orientation of faces relative to cell centres. 1 means all faces point outward; below 0.5 indicates negative volume in the documented definition |
| Minimum volume change | VolumeChange, all fluid cells | Cell volume relative to the largest neighbour, capped at 1. Siemens identifies values at or below 1e-5 as suspect. The export trigger 0.01 is intentionally more inclusive |
| Maximum skewness angle | SkewnessAngle, all fluid cells | Numerical degrees despite dimensionless STAR units. Do not convert the returned value from radians. Siemens recommends avoiding values over 85 degrees for robustness |
| Invalid-cell occurrences | NegativeVolumeCells + UnclosedCells + DegeneratedFeCells from mesh report | May double-count a defective cell; zero requires all three checks zero. Missing report entries remain absent |
| Detected prism layer count | PrismLayerNumber on foil boundary | Geometric detection; wall faces receive total detected layer count. This is not the nominal mesher input |
| Detected total stack thickness | PrismCellThickness on foil boundary, m | Boundary values denote detected total stack thickness; volume-cell values denote individual cell thickness |
| First-layer thickness range | PrismCellThickness on fluid cells with 0.5 <= PrismLayerNumber <= 1.5 | Detected first cells, not a guarantee of mesher topology classification. Does not establish y+ |
| Any-layer coverage | AreaAverage of indicator PrismLayerNumber >= 0.5 over foil | Fraction of intended foil wall area, not ratio of prism cells to all volume cells |
| Full-stack coverage | AreaAverage of indicator PrismLayerNumber >= 14.5 over foil | Fraction of foil wall area with all 15 detected layers |
| Approximate memory | Sampled sum of matching STAR/MPI process working sets | Sample maximum, not true peak. Shared pages can be counted repeatedly; see resource_method.json |

All boundary coverage reports use `fluid / HF_v2 2.ColoredFace1` and the Volume Mesh representation. The lower domain wall has prism meshing explicitly disabled in the baseline and is excluded from the intended foil coverage denominator.

The geometric prism detector is distinct from the prism mesher's log message about collapsed subsurface faces. A zero count in that meshing phase does not certify full-stack coverage everywhere. The detector also has topology-dependent limitations. Locate reduced stacks and inspect sections before interpreting every detected reduction as a true collapsed layer.

XYZ tables sample non-vertex data on the selected threshold population. The screening macro caps a table at 100,000 elements; the follow-up ExportPrismLocations macro can export up to 1,000,000 foil elements to local storage for spatial inspection. Counts and area fractions are different quantities and should not be interchanged.

Installed help references:

- C / CellQuality: `GUID-D40B8737-96C9-4B5A-B2FB-FB93F54316D8.html`.
- F / FaceValidity: `GUID-4259E11D-C03C-4C8F-A9CF-A6C0B791B81E.html`.
- V / Volume and VolumeChange: `GUID-E85256E7-732B-4C04-9155-A8CC86A46128.html`.
- S / SkewnessAngle: `GUID-89D0C6B8-1DA4-4F40-BD53-5F00495AF6A9.html`.
- P / Prism diagnostics: `GUID-1F005C26-8A91-40D9-9F2C-81CA7D10BBDD.html`. The runtime enumeration confirms the program name PrismLayerNumber; the help entry has an inconsistent repeated function-name label.

Revision-2 calibration exports contained an erroneous skewness conversion. They are preserved under audit/integration_attempts and excluded from the authoritative revision-3 comparison. The raw STAR skewness report agreed with the corrected degree interpretation.
