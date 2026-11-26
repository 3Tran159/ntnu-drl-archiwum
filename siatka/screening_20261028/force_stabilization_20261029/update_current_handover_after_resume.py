from pathlib import Path
import datetime,json,shutil
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
now=datetime.datetime.now().astimezone();tag=now.strftime('%Y%m%d_%H%M%S')
s=json.loads((R/'wave_foil_run_state.json').read_text(encoding='utf-8-sig'))
text=f"""CURRENT HANDOVER - {now.isoformat()}
User returned from meeting and explicitly resumed W01 from saved0.168s; dashboard publication freeze is lifted.
Actual owned continuation: {s.get('case')}, controller{s.get('controller_pid')}, server{s.get('server_pid')}, launcher{s.get('launcher_pid')}.
Inspect actual processes, root queue.lock, wave_cycle_continuation_r2.lock and wave_foil_run_state.json before acting. Never duplicate or restart completed controllers. No reinitialization was used. Source checkpoint and native force fingerprint verified.
Latest progress at this handover: {s.get('progress',{}).get('time_s')}s. The active controller remains running.
Period T=0.8472673206891129s. User says stop as soon as cycles repeat;10 is typical, NOT a minimum. Diagnostic cap20T. Authoritative early policy: wave_cycle_policy_current.json, wave_periodicity_current.json, watcher22748/watch_wave_periodicity_early.py. Last4 complete cycles are compared; missing initial partialcycle excluded. The already-running controller's legacy min10 assessment is superseded by watcher STOP markers. Do not silently restore10minimum.
User accepts previously observed mass residual for exploratory waves. Historical0.01% remains diagnostic; all physical/resource/source guards retained. Repeatability is not force accuracy or final grid/time/reflection acceptance.
Own STAR server stays open after normal saved stop. Existing37216 controller holds rootlock until server exits. Separate HF_012_C003_regular_waves must remain untouched.
Both original dashboards and dashboard_work_20261030 copies now update via build_manual_dashboard_copy.py and local service36724 at http://127.0.0.1:8771/. Meeting versions archived. Do NOT restart old update_status/watch_dashboard_status writers; they would overwrite integrated panels.
New requests in progress: defaultCD/CL, ETA to10T from measured recentcost, real saved-field sideview, followlatesttime unlessmanualpan. Autonomous all-wave controller+HTML+rescue handover requested but NOT yet ready/armed. Read autonomous_campaign_preparation_review.json for exact domain dependencies; L10 cannot use append-only extender. Never claim unprepared domainsready.
Heartbeat automation remains paused. Local W01 controller/watchers operate independently of Work.
Prior handover preserved in handover_history_{tag}.txt.
"""
shutil.copy2(R/'RESUME_AT_HOME.txt',R/f'handover_history_{tag}.txt')
(R/'RESUME_AT_HOME.txt').write_text(text,encoding='utf8')
for name in ['overnight_plan_20261029.json','wave_numerical_review_current.json']:
 p=R/name;d=json.loads(p.read_text(encoding='utf-8-sig'));shutil.copy2(p,R/f'{p.stem}_history_{tag}.json')
 if 'current_pause' in d:d['historical_meeting_pause']=d.pop('current_pause')
 d.update(updated_at=now.isoformat(),status='exploratory_W01_saved_state_continuation_active',current_operation={'case':s.get('case'),'controller_pid':s.get('controller_pid'),'source_time_s':.168,'policy':'early last4 complete repeatable cycles;10 indicative;20 diagnostic cap','authoritative_repeatability':'wave_periodicity_current.json','dashboard_publication':'originals_and_work_copies_authorized','autonomous_full_campaign':'requested_preparation_in_progress_not_armed'})
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'handover':str(R/'RESUME_AT_HOME.txt'),'case':s.get('case'),'progress':s.get('progress'),'status':s.get('status')},indent=2))
