# NTNU SCIENCE — Active Flap Live deployment and acceptance
**Verified:** 2026-11-03 (Europe/Oslo)  
**Project:** F:\ntnu\flap_control\project_dashboard  
**Local:** http://127.0.0.1:8787/#ramp  
**Private Tailscale HTTPS:** https://thinkpad-lucjan.tailcea0dc.ts.net/#ramp

## Deployed behavior

- Removed the full homepage heading, including both the original "Hydrofoil Research" and replacement "NTNU | CFD Research". The Overview begins with project state and the current experiment.
- Added a direct **Flap Live** navigation route and a compact, data-driven Overview summary fitting above the fold at a 390x844 phone viewport (current status card ends ~364 px).
- Added independent read-only dynamic API \`/api/ramp\` backed by \`ramp_live.py\`, and front-end \`ramp_live.js\` / \`ramp_live.css\`.
- Supports native real-time ramp kinematics, hydrodynamic forces, safety, mesh quality, native STAR iteration residuals, dynamic CL(δ)/CD(δ)/Mh(δ), signed power and hinge-moment-versus-rate.
- All time-history curves use the same physical-time x-range and selected native time cursor; independent residuals use solver iteration, never invented physical timestamps.
- Window selection (entire / 100 / 50 / 20 recorded rows), synchronized zoom, signal visibility toggles, nearest native sample readback, PNG and CSV export.
- The visualized time history is joined by experiment ID and actual controller output paths, never a fixed run folder. Recorded time replaces overlapping history samples on restarts; no synthetic or interpolated missing steps.
- Project status RUNNING requires an active owned PID and a recently changed complete native CSV. Explicit controller states are represented; stale source files never imply RUNNING.
- Files \`.sim\` and \`.simh\` are never opened by the monitor. All checkpoints are represented only by controller metadata.

## Source discovery and provenance

Primary controller metadata:
- \`F:\ntnu\flap_control\hydro_validation_2606_20261102\NIGHT_QUEUE_STATE.json\`
- \`F:\ntnu\flap_control\hydro_validation_2606_20261102\NIGHT_STATUS.json\`

Experiment: \`RAMP_C0_PLUS2_S5_20261103\`, controlled by \`RampPlus2Run.java\`.

Current experimental segments:
- \`cases\SP_C_split0_overset\ramp_plus2_20261103_093316\` (5 smoke-test samples).
- \`cases\SP_C_split0_overset\ramp_plus2_20261103_094340\` (73 production-ramp samples).
- 78 distinct physical-time samples, sourced from native \`history.csv\`; no fabricated or duplicated steps.

Additional diagnostics:
- bounded read-only tail of controller's native STAR console log under \`runs\RampPlus2Run_SP_C_20261103_094340.log\` for actual residuals, plotted against *solver iteration*;
- ramp CSV for floor counts, Overset error cells, pressure, mass imbalance and quality;
- reported saved checkpoint paths from controller metadata only.

### Final *recorded* ramp status (not a live solver advance)

| Variable | Last recorded |
|---|---:|
| Controller state | FAILED |
| Physical time | 0.806 s |
| Native ramp step | 73 |
| Native iteration | 14,680 |
| Ramp fraction | 78% |
| Actual δ | 1.85113244° |
| Recorded dδ/dt | 8.833968°/s |
| CL | 0.3955824035 |
| CD | 0.00994423789 |
| Fx | 38.3410 N |
| Fz | 1547.8745 N |
| Mh | −16.74013 N·m |
| pabs,min | 12.333273 kPa |
| Diagnostic threshold | 12.340000 kPa |
| Margin to threshold | **−6.727 Pa** |
| Signed Pmech | −2.5810 W |
| Relative mass imbalance | 1.8183e−8 |
| Overset error cells | 0 |
| k / omega floor cells | 0 / 0 |

Status is explicitly FAILED based on the controller and low pressure. No solver restart was attempted. The ramp was not completed to 0.850 s; all dynamic parametric results are diagnostic, not static polars.

**Power convention:** computed signed native hinge moment × prescribed angular rate converted from degrees per second to radians per second. Direction/sign orientation of stored hinge moment has not been independently audited. This is neither electrical actuator consumption nor whole-craft energy consumption.

## Verification

1. Ramp integration API / source integrity / continuity / restart and failure-state cases: **46/46 PASS**, recorded in \`RAMP_TEST_REPORT.json\`.
2. Existing dashboard tests, B0/C0 independent CSV comparisons, offline/stale regression and read-only source snapshot: **49/49 PASS**, \`TEST_REPORT.json\`.
3. Deployed desktop/mobile Chrome tests: **36/36 PASS**, \`RAMP_DEPLOY_BROWSER_REPORT.json\`.
4. Source checks independently compared the current ramp \`CL\`, \`CD\`, \`Mh\`, \`Fx\`, \`Fz\`, angle and pressure to the exact native CSV row; signed mechanical power verified by separate calculation.
5. Test simulations (in memory only) covered HOLD, FAILED, COMPLETE, STALE, absence of PID, stale data and restarting from overlapping segments.
6. At 390x844, no horizontal overflow, native status and primary experiment metrics fit above fold. Chart SVG axis geometry was adjusted specifically for mobile legibility.
7. PNG export and CSV export were tested as real files downloaded by headless Chrome inside this dashboard directory (not just button interactions).
8. Historic B0/C0, Waves and Mesh tabs continue operating.
9. Existing campaign source sizes and timestamps unchanged during integration tests; there were no dashboard-initiated source writes.

### Screenshot files on the ThinkPad
- \`screenshots\desktop_overview_cdp.png\`
- \`screenshots\desktop_ramp_live.png\`
- \`screenshots\desktop_ramp_kinematics.png\`
- \`screenshots\desktop_ramp_parametrics.png\`
- \`screenshots\mobile_ramp_overview.png\`
- \`screenshots\mobile_ramp_live_390.png\`
- \`screenshots\mobile_ramp_forces_390.png\`
- \`screenshots\mobile_ramp_parametrics_390.png\`
- Existing validation and Waves screenshots are retained.

### Secure network

Tailscale Serve is configured privately:
\`https://thinkpad-lucjan.tailcea0dc.ts.net\` → \`http://127.0.0.1:8787\`.

The private HTTPS endpoint returned HTTP 200 with the correct experiment ID and source values in a check from the ThinkPad. The tailnet-only status is verified. No port forwarding or public Funnel configured. Safari on the physical iPhone has not been separately instrumented after this deployment.

## Lifecycle

- Continue using \`START_DASHBOARD.cmd\` for the local app, \`stop_dashboard.ps1\` to stop *only* the dashboard and \`PHONE_ACCESS.ps1\` for a private Tailnet address.
- This dashboard auto-refreshes every 15 seconds regardless of ChatGPT/Work presence; it never manages solver work.
- Backup prior to integration: \`backup_before_ramp_20261103_095430\`.
- Scientific limitations: no accepted full-vehicle net power, no validated dynamic flap control savings, no static +2° polar, no grid/time-step independence.
