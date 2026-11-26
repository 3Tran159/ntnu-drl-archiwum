# NTNU Science · Project Control Center

Independent, read-only local web application for the hydrofoil / active flap research project.
Location: F:\ntnu\flap_control\project_dashboard


## Live ramp integration (2026-11-03)
The Overview no longer displays any hero title. It starts directly with scientific status and a real current-experiment summary. The "Flap Live" navigation tab reads `/api/ramp`, auto-discovers controller-owned experiment segments, shows 18 source-backed SVG charts with shared physical-time cursors and zoom, and offers verified PNG/CSV export. Native STAR residuals are independently labelled by iteration, not falsely aligned in physical time. Current ramp is a diagnostic FAILED run due to minimum pabs below 12.34 kPa.

Open: http://127.0.0.1:8787/#ramp  
Private HTTPS (Tailscale): https://thinkpad-lucjan.tailcea0dc.ts.net/#ramp  
Report: `RAMP_ACCEPTANCE_REPORT.md`. Test artifacts: `RAMP_TEST_REPORT.json`, `RAMP_DEPLOY_BROWSER_REPORT.json` (46/46 and 36/36 PASS).  
Screenshot previews: `screenshots\desktop_ramp_parametrics.png`, `screenshots\mobile_ramp_overview.png`, `screenshots\mobile_ramp_forces_390.png`.  
This app **never controls or restarts STAR**, W04 or the campaign queue.

## Start
Double-click START_DASHBOARD.cmd (or in PowerShell: .\start_dashboard.ps1).
Open: http://127.0.0.1:8787
Health: http://127.0.0.1:8787/api/health

Python 3.10+ is required. Standard library only; no package installation, licensing, CFD solver, internet access or access to the Work session is required. A dashboard.pid file and server.log are created inside this folder. A detached Python process survives closing the ChatGPT or browser window. If Windows is restarted, run START_DASHBOARD.cmd again. Optional automatic logon launch requires explicit user setup through Windows Task Scheduler; no such system-level change is made without permission.

## Phone
Preferred: use the already installed Tailscale on both ThinkPad and phone. Current audit observed 'NoState' (no connected Tailscale IP). Log in to the same private Tailscale tailnet on both devices, then run .\PHONE_ACCESS.ps1 in this folder. It restarts ONLY the independent monitor so the server can bind the authorized Tailscale 100.64.0.0/10 address, and prints your exact phone URL. Do not forward port 8787 on your router. Tailscale availability is verified at startup.

Alternative trusted LAN: start with 'python server.py --bind <ThinkPad-private-LAN-IP> --no-tailscale', then open http://<same-IP>:8787 from the phone on that network. This manual opt-in binds only the named interface; firewall policy may require user-controlled configuration. Do not expose on 0.0.0.0 or WAN without adding authentication.

## Sections
Overview; CFD Live; Validation Lab; Mesh & Overset; Waves Lab; Active Flap; NDLL vs URANS; Surrogate & DRL; Computer & Computation; Experiment History.

- Overview is responsive and compact on mobile.
- CFD Live: actual CSV traces, selectable channels and windows, native residuals, SVG export, automatic 15-second refresh.
- Validation: B0 / C0 last-25-row CL, CD, force and hinge moment means, percentage deltas and precise provenance. Results are DIAGNOSTIC until scientific gate is approved. A0 histories also remain available.
- Mesh: native mesh review, region counts, actual STAR-exported images only.
- Waves: separate W01/W02/W03 project acceptance flags, real W02 force histories and measured VOF surface probe, W03 smoke history, PRE_W04 calm preparation. W01 passes qualitative scope only; quantitative wave-added resistance is not approved.
- Flap: true geometry / hinge location, 100-step K0 +/-5° recorded angle versus time and native Overset checks. K0 is FROZEN-FLOW kinematics, not hydrodynamics, CL/CD or actuator power. Unperformed hydrodynamic and phase sweeps are clearly not started.
- NDLL and DRL: intentionally no data until actual validated science is supplied.
- Hardware: available Windows RAM/disks and NVIDIA telemetry; missing sensors are N/A.
- History: native review JSON records and decisions from JSONL.

## Read-only policy
The server accesses campaign and wave records with direct read-only file handles. It never imports, starts or sends commands to STAR-CCM+, never changes a queue, never writes to campaign directories, and never hashes large .sim/.simh files. The only writable outputs are local logs and dashboard.pid in this dashboard folder.

Source updates are snapshotted by size / mtime, with incomplete CSV trailing records ignored; source errors are logged in server.log. A RUNNING badge is withheld unless independently corroborated by fresh process/progress evidence. Presence of historical JSON operation=RUNNING is not sufficient. Unknown sensor data and unperformed experiments are explicitly marked N/A / NOT STARTED.

## Scientific caveats
B0 and C0 are different run branches with non-overlapping physical time windows. Their last-25-row comparison is a technical proof-of-concept screen, not validation against experiments, time-step independence, full 3D hydrofoil or vehicle energy prediction. The dashboard traces data paths, windows and status from source files; accepted C0 for kinematics is not equivalent to an approved hydrodynamic result.

## Routes
GET /api/snapshot: aggregate status, hardware, geometry, validation, images and source provenance.
GET /api/series?id=B0|C0|K0|A0|W02|W03|W04pre: actual numeric histories, native residuals and wave gauges where present.
GET /api/history: review/decision timeline.
GET /api/health: service health (always read-only).
GET /media/<whitelisted-image-key>: select actual STAR-exported imagery.
Any unknown case or image path is rejected. No mutation APIs exist.

## Tests
Run: python test_dashboard.py (last verified 49/49 PASS).
Run: node browser_test.mjs (last verified 19/19 PASS; uses installed Chrome and Node).
Screenshots stored in screenshots\*.png, including desktop_overview_cdp.png, desktop_validation.png, desktop_kinematics.png, desktop_waves.png, mobile_overview_390.png, mobile_live_390.png, mobile_validation_390.png, mobile_kinematics_390.png, mobile_waves_390.png.
Reports: TEST_REPORT.json and BROWSER_TEST_REPORT.json. Re-run tests whenever needed.
For user-visible scientific claims, always check the freshest review against the explicit current checkpoint and window.

## Safe shutdown
PowerShell: .\stop_dashboard.ps1 ; verifies process ownership before stopping only this dashboard.
