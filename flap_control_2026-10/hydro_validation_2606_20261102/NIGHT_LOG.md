
## 2026-11-02 — night campaign activation

User authorized active scientific supervision, a local serial executor, max 8 CPU and no GPU, with separate checkpoint copies. PRE_W04/C01/other campaigns remain untouched. W04, waves and DRL are excluded from this task.

C0 URANS completed 150 steps at t=0.3004 s, dt=0.002 s. Last-window CL=0.37536625, CD=0.006478087, Mh=-11.366389 Nm. All three final windows of CL, CD and Mh are stable; external mass imbalance maximum over the last 75 steps is 3.28333e-5. Minimum absolute pressure over the run is 19985.145 Pa, above the required 12339.215 Pa.

Qualification remains pending: the earlier Overset Mesh export contains undefined floating-point sentinels and cannot prove zero connectivity errors. Volume Mesh exports contain valid active-cell data. Cross-body solid intrusion was absent in that export; deviations against each body's own original polygon must be distinguished from the discretized wall. Native inspection now tests the full representation and underlying finite-volume representation without advancing or saving the simulation.

Auto-review rejected a proposed log-based license reuse and a one-step audit. Neither rejected action was executed. Standard native licensing failed. The user then explicitly approved reuse of this campaign's existing Power on Demand license. The approved key is supplied only to the STAR child environment, never printed. Read-only audit PID556 was launched with one CPU.

A 15-minute Work heartbeat was requested through the app tool, but creation failed because that tool requires approval while its approval policy is never. No heartbeat was created; do not claim scheduled supervision. Active-session supervision and the local executor are separate mechanisms.

## 2026-11-02T22:23:52.980127+01:00
STAR 2606 actually advanced C0 from 0.3004 to 0.3024 s (timestep 152, iteration 2266), then saved error_checkpoint.sim and exited after an audit guard. API bytecode shows FullMeshViewRepresentation.isEmpty() unconditionally returns true; that guard was invalid. Direct report/table extraction on this representation also gave invalid fields and cannot certify connectivity. Native interface diagnostics and pressure/shear force decomposition are now queued. Initial read-only attempt hit a second API getter mismatch (EnabledZeroDonorCheckOption vs actual ZeroDonorCheckOption); corrected exact property read. No physical conditions changed. Queue PID 10260 is serial and held against all deflections while the CL/CD bias remains unexplained. PRE_W04 untouched.

### 2026-11-02T22:32:50.389311+01:00 — B/C scientific hold
C-B instantaneous lift difference is 185.809 N; 94.1% occurs on the fixed main foil. Drag decreases by 2.647 N despite a 3.507 N increase in viscous drag; pressure drag decreases by 6.154 N. Cp shows jumps within the overlap/hinge area. C has recurring turbulent-viscosity limiting in one cell; B has none. This is a mesh/interpolation/turbulence diagnostic concern, not approved hydrodynamic benefit. Exact cause pending full native audit.

## 2026-11-02 22:45 — complete connectivity audit and bounded causal test
The correct full-cell export is an XyzInternalTable on a midspan PlaneSection using Overset Mesh. Direct region reports/tables on that representation produced invalid values and were excluded. Full count: 361532 = 252161 active + 106812 inactive + 2559 acceptors; errors=0; difficult interpolation codes 4–6=0; min volume=9.0260374e-12 m³; min quality=0.0507743. Interpolation types: distance weighted 1377, linear quasi-2D 867, ghost 315. Maximum native size ratio 9.2119 near the main foil surface. This passes connectivity, not hydrodynamic accuracy.

Wall-distance values were compared to the native geometry in the near-main-foil region; medians are essentially 1.0, with small surface-discretization deviations. There is no evidence of a missing main-wall distance across the Overset regions. Turbulence is problematic: C has 1085 active omega-floor cells, 54 k-floor cells and one viscosity-ratio-capped cell (100000), whereas B has none and maximum viscosity ratio about 1483.5. Saved plots show the difference in the overlap and hinge region.

Work authorized one bounded causal test, C0InnerIterationTest.java, from t=0.3024 s, 361532 unchanged cells, 8 CPU/no GPU, dt=0.002 s, changing ONLY inner iterations 15 to 40. Minimum 100, maximum 150 further steps; checkpoint every 25. Native full-cell connectivity check runs before, after first step and at the end; fatal native donor checks stay enabled throughout. First actual progress confirmed to t=0.3084 s. No deflections authorized. Controller handover refreshed the dashboard without stopping or duplicating STAR.

2026-11-02T23:08:20.350727+01:00
Conclude inner-iteration diagnostic at next completed physical timestep; preserve native paused_by_marker status, full final audit and checkpoint. Not a completed hydrodynamic qualification.
At least 100 physical steps and three stable force windows at steps50/75/100; CL/CD bias persists. More inner iterations do not explain dominant B/C discrepancy. Omega/viscosity pathology remains.
Next: Only separate C0 distance-weighted interpolation diagnostic from saved 40-inner control after checkpoint/native-process verification.

2026-11-02T23:09:42.116403+01:00
Inner40 saved at t=.5184 (108 steps), SHA256 c0f2dbd97b39f82fac4b7a8f2a517ad9cf81db0133ea7f7d1e423d7c214ac0f9. Native exit0, no owned STAR children. Intentional paused status retained.
Next approved: C0 distance-weighted interpolation only; no angles. Full fields and residual normalization exported before change and every25 steps.

2026-11-02 23:13 Europe/Berlin — dalsza lokalizacja problemu interpolacji
Pełny eksport rozdzielono według rzeczywistego typu interpolacji. W FlapOverset: 415 akceptorów LinearQuasi2D, maks. stosunek rozmiarów 7,0535 (x=0,757963 m, z=0,091827 m); 147 z nich ma stosunek >2. Dodatkowo 146 akceptorów używa interpolacji z komórkami lustrzanymi przy symetrii (typ7), maks.9,2119. Tak więc duża dysproporcja rozmiarów nie dotyczy wyłącznie typu7. Nie jest to samo w sobie dowodem przyczyny błędu sił. Źródło: validation/C0_size_ratio_by_interpolation.json; znaczenie typów sprawdzone w lokalnym podręczniku STAR2606 (GUID-E2FC1BB1-3676-4C83-AA10-22E15160F6BC).
Test odległościowy zmienia tylko interpolację względem zachowanego źródła40-inner. Oceniamy siły, Cp, ograniczenia k/omega, lepkość turbulentną oraz kontrolę energii średniego przepływu. Nie utożsamiamy zgodności CL/CD z pełną walidacją.

2026-11-02T23:15:44.598032+01:00
Initial isInitialized query occurred before native mesh/field loading. Replace this guard with exact saved-time and Fx/Fz/Mh/CL/CD readback against source history. No initializeSolution, clearSolution or remesh call. Previous launch solved zero steps; original control checkpoint retained.

2026-11-02T23:20:38.999716+01:00
Saved physical time/forces successfully re-read without initialization; optional residual accessor AutoNormalizeIndex refers to absent native property. Removed this accessor; normalization factor and residual exports retained, optional errors explicitly recorded. Zero steps were solved; scientific gate remains false.

2026-11-02 23:21 — odczyt pól kontrolnych po teście 40 iteracji
Checkpoint t=0,5184 s został odczytany natywnie; Fx/Fz/Mh/CL/CD zgodne z historią do dokładności zapisu, bez initializeSolution/clearSolution. isInitialized nadal=false pomimo poprawnych pól, więc flaga nie nadaje się tu do oceny utraty rozwiązania.
Porównanie aktywnych komórek C15 → C40: omega na dolnym ograniczeniu1085 →1087; k54 →54; lepkość turbulentna na limicie1 →1. Maksymalna prędkość lokalna30,5215 →30,5202m/s w tej samej komórce. Kontrolny parametr energii średniego przepływu462,574 →462,543kPa (w B164,072kPa). Więcej iteracji nie usuwa również lokalnej anomalii pól. Nie stosujemy tej wielkości jako ścisłej uniwersalnej granicy Bernoulliego.
Źródło: validation/C0_inner40_native_fields.json. Akceptacja C0 nadal zablokowana.

2026-11-02T23:40:35.415150+01:00
Distance interpolation preserves valid connectivity but does not cure anomalous fields: at step50 omega-floor1368 versus1087 control; local mean-flow energy screen425kPa versus164kPa B. Last25 CL+15.08%,CD-10.84% relative B. Do not continue for a formal force-window pass.
Graceful stop after current physical step with final full audit, field exports, and unique checkpoint. Mark diagnostic unsuccessful/incomplete qualification, never approved.
Next: Read-only native solver frozen/model/motion/wall-status audit; then decide between clean-state control and overlap-resolution repair.

2026-11-02T23:43:14.475342+01:00
Distance remedy rejected after73steps, saved t=.6644, native exit0, no owned solver children. SHA256 e3594c9b927545954e305d5b062672dec93f3a418df2a1ebe99885b6c2c5f375. Native final all361532cells:0errors,0difficult,all2559acceptors distance weighted. Physical/accuracy qualification incomplete. Next: C/B read-only setup audits only.

2026-11-03T00:00:17.480078+01:00 Fresh C0 DISTANCE initialization approved on protected pre-motion mesh, same physical conditions and geometry. Native setup audit shows all foil walls active, zero grid velocity, flow and turbulence solvers not frozen. No acceptance or deflections. Steady time=0 is a separate new diagnostic, not a reset of the previous checkpoint.

2026-11-03T00:05:01.712385+01:00 Fresh DISTANCE startup diverged after40 iterations; native guard saved initialization_error.sim and exited. Initial continuity procedure alone generated pabs approximately -2.37 MPa to13.6 MPa. Next controlled diagnostic: disable continuity initialization, same source hash, physics and mesh. No accepted data.

2026-11-03T00:09:43.281619+01:00 No-CI fresh startup also rejected after50 iterations by native divergence guard; error checkpoint preserved. STOP request arrived after native error exit. No turbulence floor cells yet, so this cold-start instability is distinct from the longstanding clipped-turbulence C0 state. Next single-variable startup diagnostic disables Overset flux correction, retaining DISTANCE/no-CI. All quality/scientific gates remain closed.

2026-11-03T00:14:47.662935+01:00 No-flux startup stopped by the tighter5MPa pressure guard after10 iterations, before a trend can establish. Do NOT claim flux correction was excluded. Archived B startup also had unphysical early pseudo-iteration pressure; old C initial k/omega were uniform before steady solving, so inherited turbulence from the motion test is not established as the cause. Next: local overlap mesh resolution1mm; mesh-only audit first. Original LinearQuasi2D retained for comparison with original C0. No physical geometry change.

2026-11-03T00:20:06.001477+01:00 Overlap mesh generated424982 cells, negative/unclosed0, minQ.0580095. Full Overset audit encountered DBL_MAX unavailable fields before initialization; saved mesh-only error checkpoint. FinalizeC0MeshAudit allocates initial field storage with continuity initialization off, no iterations or mesh operations, then repeats full audit in separate output. Source preserved.

2026-11-03T00:25:13.166718+01:00 Full overlap mesh audit:424982 cells, negative/unclosed0, OversetError0 but1 type4 difficult interpolation cell; strict gate rejected it. Background304810 cells identical (max center error2.85e-14m). Max size ratio4.695 vsold9.212. Next: same mesh with DISTANCE, no remesh/no flow. Reference for future mesh comparison is saved DISTANCE control.

2026-11-03T00:30:25.452289+01:00 DISTANCE audit of1mm overlap still has1 type4 difficult acceptor, so no flow allowed. Small0.5mm patch around x.758664,z-.035147 follows installed2606 guidance. Same background source/geometry. Field storage initialized without continuity iterations before full native audit. All diagnostics and failed checkpoints retained.

2026-11-03T00:37:46.804779+01:00 Local0.5mm patch resolved original difficult stencil but a new type4 occurred atx.8943489,z-.0212401. Mesh425762, positive volumes, no native errors, minQ.0610482. Do not solve. Broaden inner-overlap0.5mm band covering both sites and original anomaly zone; keep background and geometry.750k cap/8CPU, all gates unchanged.

2026-11-03T00:46:18.399731+01:00 Inner0.5mm overlap mesh PASSED:579468 cells,3444 DISTANCE acceptors,error0,difficult0,positive volumes/Q,background304810 identical. Approved bounded steady initialization on8CPU; conservation NONE during startup and continuity initialization on, matching historical startup strategy. This does not approve forces; requires subsequent FLUX_CORRECTION/URANS comparison plus full fields/residuals/pressure review. Checkpoints250iter,cap1500,convergenceCL/CD/Mh and pressure/mass windows.

2026-11-03T00:56:26.178213+01:00 Refined C0 startup rejected at40iterations: Umax1512m/s at main leading edge, pmax543MPa, CD4.323. Full failure fields/checkpoint saved; no native Overset errors and no k/omega clipping. Approved separately recorded velocity/pressure URF0.3/0.1 on same mesh/physics; strict scientific gate remains. No deflections.

2026-11-03T01:07:40.950528+01:00 Relaxed startup paused after430iterations; complete checkpoint847104592bytes. Approve documented first-order flow/SST convection continuation on exact saved fields, no initialize/clear/remesh.8CPU. First-order result cannot be accepted; restore high-order/matched physics before comparison. No angles.

2026-11-03T01:15:38.738332+01:00 First-order recovery has zero k/omega floors and pressure above12339.2148Pa. Enabled controller pressure/mass/turbulence/Overset stop gates for all subsequent iterations; prior low-pressure numerical repair samples remain rejected. This does not qualify first-order forces.\n
2026-11-03T01:21:14.696922+01:00 Continue exact saved steady fields at native iteration1260, time0. Numerical diagnostic mode flux: flow FIRST_ORDER to FIRST_ORDER, SST FIRST_ORDER to FIRST_ORDER, Overset conservation NONE to FLUX_CORRECTION. Preserve579468-cell mesh,DISTANCE,U18,rho1000,mu.001,URF0.3/0.1,0deg geometry. No reset/remeshing. Strict pressure/mass/turbulence/Overset guards from first block. No scientific approval until matched second-order URANS is evaluated. CSV iteration=additional; native_iteration=1260+iteration.

2026-11-03T01:33:03.756128+01:00 Continue exact saved steady fields at native iteration1850, time0. Numerical diagnostic mode momentum2: flow FIRST_ORDER to SECOND_ORDER, SST FIRST_ORDER to FIRST_ORDER, Overset conservation FLUX_CORRECTION to FLUX_CORRECTION. Preserve579468-cell mesh,DISTANCE,U18,rho1000,mu.001,URF0.3/0.1,0deg geometry. No reset/remeshing. Strict pressure/mass/turbulence/Overset guards from first block. No scientific approval until matched second-order URANS is evaluated. CSV iteration=additional; native_iteration=1850+iteration.

2026-11-03T01:47:52.016431+01:00 Measured active/acceptor transition at geometric layer26-29,0.5-0.75mm from smooth main wall.36th layer near2.2mm and normal size0.35mm, closer to0.5mm Overset cells. This is a test, not assumed safe: force no active cells inside either solid before solving. Native1CPU audit only; no flow.\n
2026-11-03T01:54:14.429778+01:00 Native settings saved but 579468 statuses and coordinates identical; setting not proven effective. Recompute existing interface using supported resetInterfaces+initializeInterfaces, no solution initialization or mesh generation.

2026-11-03T01:58:46.100003+01:00 Reset+initialize did not change any cell statuses; native wall vertex containment passes with zero active centers inside either solid. Isolate deferred kernel update with all flow/turbulence solvers frozen, retain physical time0.

2026-11-03T02:09:32.092458+01:00 Even native1850->1851 frozen step left all579468 statuses unchanged. Native vertex geometry and active-center containment pass. Isolate initialization sensitivity on preserved zero-step source; do not reset saved hydro state.

2026-11-03T02:15:18.418019+01:00 Installed2606 GUID-9FBDF4AF-B3A3-4F93-A55D-A585CECD1346: reinitialization requires clearing solution storage. This copy is strictly iteration0/time0; the source1850 solution is untouched. Calling initializeSolution on already initialized zero-step storage retained exact old statuses. Previous test did not prove fresh assembly.

2026-11-03T02:20:57.210980+01:00 Actual reassembly fails: Background acceptors outside FlapOverset, ErrorStatus6, zero donor. No PDE steps; error checkpoint520766038bytes SHA256f80624ba9f078d2af01dd4d4f50f68ed751f24b548f0274615d1dcf0211f42ab. Source1850 remains intact.

2026-11-03T02:26:06.379284+01:00 All195nativeError6acceptors from whole-wall36 test are inside flap nose,x0.9325..0.9572,z-0.0134..0.05494; none outside cage. Limit protection toforewallx0.80m. Estimated36tangentialwall-cell layers~0.103m gives separation from flap nose x~0.917m; this estimate must be checked natively, not assumed valid.

2026-11-03T02:31:41.801987+01:00 Localized36 native pass:370567active,205599inactive,3302acceptors,0error/difficult; all579468cell centers/volumes exactlyunchanged. However main active-wall export lost2vertices near lower hinge; hold until coverage explained/resolved. Partition itself preserved all1163vertices.

2026-11-03T02:46:44.599086+01:00 Tight-cage mesh-only audit: physical geometry unchanged; full native mesh checks required; all flow/angles remain gated.

2026-11-03T02:50:59.855133+01:00 Tight-cage mesh-only audit: physical geometry unchanged; full native mesh checks required; all flow/angles remain gated.

2026-11-03T03:27:41.037654+01:00 Continue exact saved tight-cage steady fields at native iteration1050, time0. Numerical diagnostic mode momentum2: flow FIRST_ORDER to SECOND_ORDER, SST FIRST_ORDER to FIRST_ORDER, Overset conservation FLUX_CORRECTION to FLUX_CORRECTION. Preserve333939-cell mesh,DISTANCE,U18,rho1000,mu.001,URF0.3/0.1,0deg geometry. No reset/remeshing. Strict pressure/mass/turbulence/Overset guards from first block. No scientific approval until matched second-order URANS is evaluated. CSV iteration=additional; native_iteration=1050+iteration.

2026-11-03T03:41:03.871349+01:00 Continue exact saved tight-cage steady fields at native iteration1590, time0. Numerical diagnostic mode turbulence2: flow SECOND_ORDER to SECOND_ORDER, SST FIRST_ORDER to SECOND_ORDER, Overset conservation FLUX_CORRECTION to FLUX_CORRECTION. Preserve333939-cell mesh,DISTANCE,U18,rho1000,mu.001,URF0.3/0.1,0deg geometry. No reset/remeshing. Strict pressure/mass/turbulence/Overset guards from first block. No scientific approval until matched second-order URANS is evaluated. CSV iteration=additional; native_iteration=1590+iteration.
