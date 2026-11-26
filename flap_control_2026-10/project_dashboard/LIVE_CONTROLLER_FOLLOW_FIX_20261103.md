# NTNU Project Control Center — Live controller-follow repair
Date: 2026-11-03. Dashboard-only modifications.

## Root cause

The dynamic registry had already discovered new controller runs, but the Overview and CFD Live default view were misleading:
1. `ramp_live.js` periodically overwrote the Overview status, title and metrics with the *historical failed* `RAMP_C0_PLUS2_S5_20261103`, regardless of which experiment the controller was actually running.
2. `app.js` also overwrote the Overview with that same historical ramp on each snapshot refresh.
3. CFD Live selected an active run only on initial setup; when the controller transitioned to a different experiment, its previous selection could persist indefinitely.

## Repair deployed

- `runs_registry.py`: the read-only `/api/runs` payload now exposes `active_run_id`, `active_controller_state` and queue state from the same metadata snapshot. `/api/run_series` preserves native phase, stage, velocity and measurement-eligibility metadata when recorded.
- `app.js`: Overview now follows the controller's active experiment, with native CL/CD/angle/pressure/time from its CSV. When the controller stops, it shows the latest recorded experiment as an archive instead. A stopped/stale source is not presented as RUNNING.
- `app.js`: CFD Live has a default-enabled **Follow active run** checkbox. New controller job IDs automatically become the selected primary series as soon as a native history is available. Explicit manual run selection disables follow mode; toggling it back on resumes automatic following. Historical multi-run overlays remain selectable.
- `ramp_live.js`: archived failed ramp data remain accessible in Flap Live, but that module no longer writes to the Overview or impersonates the current experiment.
- `index.html`, `runs_registry.css`, `ramp_live.css`: compact current-experiment title is dynamic and wraps on 390px mobile widths. The quick card links to CFD Live rather than always opening the archived ramp.

No CFD source, macro, checkpoint, STAR process, autonomous queue, or Work process was changed.

## Actual controller observations

At 14:08 local time, `RECOVERED_FIXED_PLUS2_SWEEP_20261103_RUN` was actively progressing at about t=1.186 s with ~198 measured steps, CL~0.29708 and CD~0.010067. Its history was visible in `/api/runs` as ACTIVE even while the Overview was displaying the older failed ramp.

The controller subsequently stopped at approximately 14:14 local time. Current final recorded data for that experiment:
- Native history: 211 unique rows
- Last physical time: 1.2120000000000009 s
- Last CL: 0.2940873750789219
- Last CD: 0.010275884816327805
- Final metadata: completed, NOT scientifically accepted (DIAGNOSTIC)
- Current queue: CONTROLLER_STOPPED
- `/api/runs` currently contains 22 entries, including the failed 78-sample ramp. No new samples are assumed.

## Test evidence

- Staged browser regression: **61/61 passed**, including current Overview case, no stale-ramp override, mobile 390px no horizontal overflow, dynamic run registry, Live default selection, manual override, existing Validation/Waves/Flap Live/Flow Field and exported PNG.
- Read-only Python registry / CFD integrity regression: **52/52 passed**.
- In-memory controller-active simulation (no source file writes): `/api/runs` correctly exposed `active_run_id=exp:RECOVERED_FIXED_PLUS2_SWEEP_20261103` when a synthetic metadata copy held an active job. The real controller was not affected.
- Production after safe restart: health OK, PID 35700, 22 runs, latest experiment correctly returned 211 rows, archive ramp still 78 rows.
- Private tailnet HTTPS: `https://thinkpad-lucjan.tailcea0dc.ts.net/api/runs` returned HTTP 200 and the new index included the follow-active control.
- No solver or CFD queue mutations.

## Access and files

- Local: http://127.0.0.1:8787/#live
- Private Tailscale: https://thinkpad-lucjan.tailcea0dc.ts.net/#live
- Overview: https://thinkpad-lucjan.tailcea0dc.ts.net/#overview
- Test report: `CURRENT_RUN_BROWSER_REPORT.json`
- Screenshots: `screenshots\desktop_overview_cdp.png`, `screenshots\mobile_overview_current.png`, `screenshots\desktop_registry_live.png`.
- Backup before changes: a `backup_overview_live_fix_20261103_*` directory inside `project_dashboard`.

Remember: historical fields in Flow Field remain last true exported CFD snapshots, not the most recent solution unless a native field export exists at the current time.
