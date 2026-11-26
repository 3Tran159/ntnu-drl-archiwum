# NTNU Science / Project Control Center
## Implementation and acceptance report | 2026-11-03

### Installed app
- Project: F:\ntnu\flap_control\project_dashboard
- Local URL: http://127.0.0.1:8787
- Process: detached Python stdlib HTTP server started with START_DASHBOARD.cmd / start_dashboard.ps1
- Self-contained: zero external JS/CSS dependencies, no Python packages, no STAR-CCM+ license, no Work session dependency
- Read-only: reads JSON/JSONL/CSV, restricted real STAR images, optional external W02/W03 wave probes, OS telemetry; no POST/PUT/DELETE or solver actions
- Security: loopback listener by default; optional existing private Tailscale interface only. Router ports not opened.

### Independent data integrity verification
Run python test_dashboard.py. Final integration regression: 49/49 tests PASS (TEST_REPORT.json).
- Separate original B0 and corrected C0 histories: 100 rows each.
- Last 25 CSV rows are independently averaged and compared against API values for CL, CD and hinge moment. Zero difference within floating-point tolerance.
- B0 CL 0.32661098046588; CD 0.007191107030274.
- C0 CL 0.32561948776312; CD 0.0072459371243424.
- C0 vs B0 ΔCL −0.3035699232603051%; ΔCD +0.762470838461593%.
- Both are numerical diagnostics at 0° and have different windows. The <1% result is a technical screen, not grid independence or experimental validation.
- Native residual CSVs for both are actually read.
- Original C0 Overset had 361532 cells and a near-wall artifact. Corrected C0: 333939 cells (304810 Background, 29129 FlapOverset), 1481 acceptors, zero error/difficult interpolation cells in recorded mesh review.
- Native 100-step frozen-flow kinematic K0 history read. +/-5° motion and actual angle errors recorded; no fictitious CL/CD values; zero recorded overset errors in every step. Explicitly not a hydrodynamic force result.
- W01 qualitative wave-added resistance verification accepted, quantitative validation not accepted. W02/W03 remain pending. W02 sampled force history and eta(t) gauge at x=-0.5 m are real source data; W03 is smoke test only.
- Stale status and offline read handling tested; no fabricated RUNNING from historical JSON.
- Source-file snapshot sizes and mtime unchanged across integration test.

### Browser & mobile acceptance
Run node browser_test.mjs. Final Chrome DevTools-based result: 19/19 PASS (BROWSER_TEST_REPORT.json).
- Desktop: 1440x950, no horizontal overflow, real source connected, B/C traces and numeric table available.
- Kinematics: true K0 motion chart and frozen-flow status.
- Waves: true W02 CL(t) and VOF eta(t) measurement.
- Mobile: emulated touch viewport 390x844, no horizontal overflow on Overview, Kinematics and Waves.
- Critical mobile status finishes around y=409 px, well within one 844 px screen.
- Charts render and navigation works without page reload.

### Screenshots on the ThinkPad
- screenshots\desktop_overview_cdp.png
- screenshots\desktop_validation.png
- screenshots\desktop_kinematics.png
- screenshots\desktop_waves.png
- screenshots\mobile_overview_390.png
- screenshots\mobile_live_390.png
- screenshots\mobile_validation_390.png
- screenshots\mobile_kinematics_390.png
- screenshots\mobile_waves_390.png

### Current limits and not-yet-complete acceptance gates
- No full quantitative wave-added-resistance validation, no full NDLL/URANS matching, no accepted moving-flap force/energy sweeps, no surrogate/DRL training. Planned sections explicitly show NO DATA/NOT STARTED.
- A full grid/time convergence study is still pending. Real mesh evolution and quality can be displayed, but a fabricated convergence curve is prohibited.
- Live process status relies on fresh native process + progress; if no advancing evidence, status defaults HOLD even while background Java processes exist.
- CPU/GPU native counters are provided when readable. CPU temperature and GPU throttling cause are N/A without verified sensors.
- Local browser URL is ready. Tailscale is installed but was in NoState during audit, so no private phone URL is presently available. User must connect Tailscale on both devices and run PHONE_ACCESS.ps1, or opt into a trusted private LAN bind.
- The dashboard survives closing ChatGPT and the browser. No system-level auto-start service is installed because all modifications must remain inside project_dashboard. After Windows reboot use START_DASHBOARD.cmd (or create an OS logon trigger by separate explicit user action).
- External Work controller actively updates campaign sources; current state must always be read live, not frozen from this report.

### User actions
1. Open http://127.0.0.1:8787 locally.
2. If necessary, double-click START_DASHBOARD.cmd to start the monitor, without touching CFD.
3. In a private Tailscale network, run PHONE_ACCESS.ps1 to obtain the exact phone URL.
4. To verify integrity, run python test_dashboard.py and node browser_test.mjs.
5. To stop only this monitor, run stop_dashboard.ps1.
