from pathlib import Path
import datetime,json,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
now=datetime.datetime.now().astimezone().isoformat();tag=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
text=f"""DASHBOARD LIVE ARRIVAL AND READABILITY UPDATE — {now}
GPU campaign is unchanged: fresh W01a full-height restart controller2896, launcher228. Inspect current state/locks before any solver action.
Both dashboards now show the case-specific first-inlet-crest forecast: target t=1.690354445s, observed near-inlet crest x=-34m at t=.250s, phase-speed extrapolation23.6053m/s. This is NOT measured arrival or cycle admission.
wave_arrival_dashboard_panel.py computes remaining physical time from actual saved history and wall ETA from the latest50 regular1ms steps. Local /api/status now includes this read-only forecast; browser polls every5s. Paused/stale/guard-failed states suspend wall ETA. Passing predicted time explicitly remains unconfirmed; do not set an analysis origin from the countdown.
Only the local HTTP service was restarted39700→7240 after process/listener identity checks. No CFD process or numerical setting was changed.
Current CL/CD DISPLAY begins at t=.200s and rescales to visible data; interactive payload/view storage updated. Full CSV history and scientific analysis remain intact.
Shared wave-case catalog has scoped wrapping/fixed desktop columns and mobile labeled cards to prevent Definition/Current-record text overlap. Final integrated screenshot QA is being recorded separately.
\n"""
p=R/'RESUME_AT_HOME.txt';shutil.copy2(p,R/f'handover_history_{tag}.txt');p.write_text(text+p.read_text(encoding='utf8'),encoding='utf8')
p=R/'RATUNKOWY_KONTYNUACJA_CHAT.txt';shutil.copy2(p,R/f'RATUNKOWY_KONTYNUACJA_CHAT_history_{tag}.txt');p.write_text(text+p.read_text(encoding='utf8'),encoding='utf8')
p=R/'dashboard_live_arrival_change.json';p.write_text(json.dumps({'updated_at':now,'http_pid':7240,'solver_unchanged':True,'forecast_source':'w01a_first_crest_arrival_estimate.json','forecast_module':'wave_arrival_dashboard_panel.py','poll_seconds':5,'display_start_s':.2,'underlying_CSV_modified':False,'arrival_confirmed_by_countdown':False,'catalog_overlap_fixed':True,'qa':'pending_integrated_review'},indent=2),encoding='utf8')
print(json.dumps({'handover_updated':now,'http_pid':7240,'solver_unchanged':True}))
