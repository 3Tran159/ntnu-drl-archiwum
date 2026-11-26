# NTNU Dashboard — Dynamic Run Registry Deployment
Date: 2026-11-03 (Europe/Oslo)

## Deployment

- Production local URL: http://127.0.0.1:8787/#live
- Private mobile URL: https://thinkpad-lucjan.tailcea0dc.ts.net/#live
- Validation URL: https://thinkpad-lucjan.tailcea0dc.ts.net/#validation
- Project root: F:\ntnu\flap_control\project_dashboard
- Server PID at final production verification: 21144.
- Tailscale Serve is configured tailnet-only; HTTPS /api/runs returned 200 OK with 19 total entries.

## What changed

- Dynamic registry discovered from local controller NIGHT_QUEUE_STATE.json (jobs + active) with explicit experiment_id grouping, falling back to run_id.
- Controller-owned history.csv sources are accessed with stable, bounded, read-only snapshots.
- Two allowlisted source roots: campaign cases and F:\ntnu\flap_control\independent_cfd_diagnostics, to include the controller-owned C0_SPEED_DOWN run.
- Newest 800 controller records considered, making future appended job IDs discoverable.
- Segments belonging to one experiment merge by physical time; later segment wins on overlapping native sample time. No interpolation.
- Historical B0/C0/A0/K0 and Waves remain selectable; failed histories remain visible, but completed does not imply scientific ACCEPTED.
- CFD Live run selector dynamically updates, including overlay checkboxes.
- Validation Lab can compare controller and historical runs with the same native physical-time axis, source provenance, last 25 measured samples and status labels.
- Automatic refresh: 15 seconds without navigation reload; Flap Live continues using its existing independent reader, not duplicated.

## Data checks

| Native source | Status | Samples | Segments | Last physical time |
| --- | --- | ---: | ---: | ---: |
| RAMP_C0_PLUS2_S5_20261103 | FAILED | 78 | 2 | 0.806 s |
| C0_SPEED_DOWN_20261103 | DIAGNOSTIC | 20 | 1 | 0.690 s |
| SPEED_SWEEP_PLUS2_20261103 | FAILED | 1 | 1 | 0.002 s |

Ramp smoke segment contains five native samples, production segment contains 73. Total 78 unique physical times. No resumed or additional sample is assumed after FAIL.

## Test results

- Dynamic registry and flow-field/source-integrity tests: 52/52 PASS (REGISTRY_FLOW_TEST_REPORT.json).
- Staging browser tests of run discovery, overlays, Validation comparison, existing Flap Live and Flow Field, desktop/mobile: 54/54 PASS (COMBINED_STAGING_BROWSER_REPORT.json).
- Historical dashboard regression, B/C CSV checks and read-only policy: 49/49 PASS (TEST_REPORT.json).
- Production /api/runs: 19 entries (12 newly discovered controller runs plus 7 static references), HTTPS 200.
- Production /api/run_series for RAMP: 78 rows, 2 segments, t_last=0.806 s, FAILED.
- Production /api/run_series for speed-down: 20 rows, DIAGNOSTIC.
- Native campaign archived sources unchanged during verification.
- Dashboard server only was restarted after verifying PID ownership. No STAR-CCM+, CFD controller, queue, solver checkpoint or W04 operation was touched.

## Screenshot files

- screenshots\desktop_registry_live.png
- screenshots\desktop_registry_validation.png
- screenshots\mobile_live_390.png
- screenshots\mobile_validation_390.png
- screenshots\desktop_flow_velocity.png
- screenshots\desktop_flow_pressure.png

## Scientific caveat

Recorded FAILED results are diagnostic evidence only. ACCEPTED is reserved for a controller-supplied explicit scientific approval; job completion is not sufficient. Time histories are overlaid at native absolute physical time (no phase shifting).
