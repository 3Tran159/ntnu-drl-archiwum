# Experimental method

## Phase I: inexpensive mesh screening

The decision is which settings generate reproducibly, satisfy local geometry/resolution constraints and offer a useful quality–cost trade-off. Geometric quality is not a measure of solution accuracy.

### Freeze the model

Archive a baseline `.sim` checksum and the exact executable/build, precision, machine, core count and licensing mode. Record geometry units, part/region selection, domain/symmetry extent, SST and wall treatment, VOF/wave settings and all mesh-operation inputs. Record all dependencies on external CAD or data. Copy or resolve those dependencies before calling a case reproducible.

Lock target y+≈55 as the study intention, along with the actual first-layer specification, layer count, growth/distribution method, total thickness, near-core constraints and local overrides. Record whether values are absolute, percentages or expressions. For a geometric stack, first height, count and growth determine total thickness; these are not four independent settings. Hyperbolic distributions require their own definition. Nominal settings may remain fixed while actual generated layers collapse; that is an output to measure and reject/review.

### Identify independent axes

Potential axes are Base Size, foil surface target, leading/trailing-edge targets, wake refinement and free-surface refinement. None is assumed to exist by that name. Audit Base Size inheritance, minimum/target sizes, curvature/proximity limits, surface-control precedence and intersecting volumetric controls. Resolve whether LE and TE can share a factor. Keep TE fixed initially if a separate parameter would exceed the budget. Resolve whether VOF controls anisotropic x/y/z spacings or a single isotropic size.

Prefer absolute h/c parameters for independence; export both h in metres and h/c. If using percent-of-base controls, explicitly calculate the percentage required for a chosen absolute target and verify the resulting control value. Fixed relative percentages are coupled when Base Size varies. A configured target can have no effect because another control dominates or a trimmed-mesh level is quantized; inspect actual resolution and effective mesh changes.

Bounds must be justified by baseline geometry and generation behavior: LE curvature, finite TE thickness, gaps, foil–surface separation, outer-prism transition, wake length and expected wave scales. Use actual wave height, wavelength, propagation direction, speed and refinement-band extent. For calm water, H=0 does not mean a zero vertical cell size; foil-generated wave scales and surface motion still need resolution. The workbook's example 0.01 m band size is not an automatic lower bound.

The current generator supports a feasible rectangular box in log absolute lengths. Establish that all combinations respect dependencies before sampling. If not, reduce/reparameterize the axes rather than rejecting many expensive trials. Store the selected bounds and their evidence in the campaign configuration. The inspected pilot uses a 0.0064–0.0128 m foil target interval with fixed Base Size. Other axes remain unbound for execution.

### Stage budgets and design

| Stage | Provisional allocation | Decision |
|---|---:|---|
| A | 3 executable pilot cases, plus 1 reserve | Baseline plus two bounded perturbations of one verified axis; this pilot uses coarsening only; reserve covers repeat or integration checks |
| B | 12 | Maximin Latin hypercube in the verified independent space, seed 20261028 |
| C | Up to 4 | One or two informative changes at a time around acceptable candidates or an observed feasibility boundary |

The total envelope is approximately 20, not a requirement to use all slots. With one or two independent parameters, a small structured design can be clearer than LHS; choose before generating Stage B. Twelve points in five dimensions are exploratory. A full quadratic in five variables has 21 coefficients including intercept, so this budget cannot support an unrestricted quadratic model. Avoid claims about detailed interactions or statistical convergence.

The first three meshes do not establish sensitivity for every axis. Check all intended control bindings before Stage B. If binding checks require more meshes, reallocate the budget rather than hiding those runs. The optional repeat estimates meshing variability and runtime noise; a single repeat does not establish a failure probability.

### Collect and classify

Maintain separate generation status, metric completeness, hard-constraint acceptance and candidate ranking. A failed case is a feasibility observation; it never receives fabricated quality values. A missing metric is unavailable, not zero. Retain the complete process log, input/readback state, generated-file paths and exact failure reason.

Define every quality metric using the installed documentation, field function, operation, selection, units and validity range. Measure cell count, generation duration, minimum cell volume, invalid-cell count, cell quality, volume-change behavior, face validity, skewness definition/units and relevant tails or threshold counts. Do not infer the meaning of a report from its name. Associate thresholds with physical locations and candidate-stage decisions, not a universal mesh score.

Local diagnostics must cover foil upper/lower surface, LE, TE, tip, prism/core transition, wake, free-surface band and refinement transitions. Export thresholded cell coordinates and local min/quantile/fraction reports where possible. Include fixed-view scenes for repeatable visual inspection. Avoid an undifferentiated global minimum as the only quality evidence.

For prism coverage use a declared intended-wall-area denominator and measured wall area carrying the prescribed layer condition. Distinguish at-least-one-layer coverage from full-stack coverage. Record missing/reduced layer area, height distribution and collapse location. Count of prism cells divided by all cells is not wall coverage. Check near-core behavior with local transition metrics and sections; do not substitute a global length ratio for Volume Change.

The model-specific extractor supplies actual scalar reports, thresholded cell coordinates, foil-area-weighted prism coverage, layer counts and thickness diagnostics. Manual evidence-backed prism/core-transition and local-resolution review remains necessary. Such records stay incomplete until that review exists. The resource monitor matches STAR/MPI processes by the encoded case session path, including ranks outside the launcher ancestry. It reports sampled sums of working sets, not an exact physical-memory peak; shared pages can be counted more than once. A file size or Python process RSS is not solver memory.

### Pareto and sensitivity

Reject infeasible, invalid, incomplete and unresolved cases before ranking. Minimize cell count, generation time and measured resource cost; maximize validated local-quality measures or minimize poor-cell fractions. Keep local-resolution adequacy as a constraint. Record every objective direction. Avoid using total count as a proxy for wave or wall accuracy.

Use rank/scatter relationships and pilot perturbations to identify likely influential axes. Report them as exploratory in small mixed-success datasets. Check whether an apparent effect is actually an inherited dependency. Analyze failure locations separately from successful metrics. Only fit a simple surrogate if there are enough feasible, independent observations and a useful held-out error check; otherwise use local comparisons.

After each stage, save a review with observed failures, Pareto candidates, resolution evidence, cost estimate and proposed next rows. Prefer one-axis local changes when attribution is the question. Explore between a feasible and failed point only if the failure has a credible parameter-dependent explanation; a license failure is not a mesh-feasibility boundary.

### Stopping rules

Before Stage B, choose practically meaningful improvement tolerances for local poor-cell fractions and cost from the pilot noise and research needs. Do not invent those numerical tolerances before observing the baseline.

Stop or reduce the experiment if the next stage exceeds measured resource budgets, if failures make the chosen region infeasible, or if all current informative proposals are below the declared improvement tolerances. Stop local refinement after two consecutive reviewed additions fail to improve the feasible Pareto set beyond those tolerances, provided critical bounds/control effects have been checked. If rankings change within the observed variability, label them unresolved and use a repeat or targeted diagnostic instead of adding arbitrary DoE rows. A stable screening shortlist is not statistical convergence or mesh independence.

## Phase II: limited CFD verification

Choose approximately 2–3 acceptable candidates representing the useful cost–quality trade-off. Start with a short, consistently initialized stability check, then run enough of the actual unsteady problem to establish repeatable statistics or phase-resolved quantities. Compare lift/drag with identical reference definitions, pressure distributions, wave elevation/pattern, achieved wall-y+ distributions, continuity and solver behavior. Use fixed warm-up and analysis-window rules appropriate to the wave encounter period and sampling uncertainty. Do not run full unsteady VOF on every DoE mesh.

For wave-added resistance, compare corresponding waves and calm-water conditions using a consistent drag sign convention and normalization. The difference can be small or cross zero. Use dimensional force uncertainty and an appropriate common reference; avoid misleading relative errors divided by a near-zero added resistance. Preserve paired mesh/physics choices and account for averaging variability.

## Phase III: systematic spatial and temporal verification

Build at least three related grid levels around the chosen mesh topology and refinement method. Keep geometry, physics, boundaries and solution processing consistent. Document local refinement ratios, wave-band resolution, wall treatment and any change in near-wall spacing. If the prism stack stays fixed, explicitly describe this as tangential/core refinement with fixed wall-normal resolution; it does not prove convergence in all directions.

Evaluate observed refinement trends and order before applying Richardson/GCI reasoning. Check iterative/statistical errors and the asymptotic range. Do not apply a monotonic textbook formula blindly to oscillatory or divergent trends. An effective ratio based on cell count can summarize unstructured grids but does not establish similarity between unrelated DoE meshes. A GCI value quantifies discretization behavior under its assumptions, not experimental validation.

Assess timestep refinement separately with adequately resolved spatial grids and comparable physical averaging windows. Assess domain extent, wave propagation/damping/reflection and incident-wave preservation separately where material. Grid refinement cannot correct an incorrect boundary condition or a mismatched reference geometry.

Reference: NASA Glenn, https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html. STAR-specific metric formulas and API calls must come from the installed 21.02.007 help/API during integration.
