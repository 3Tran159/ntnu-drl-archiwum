"""Record completed dashboard work; preserves the user pause and all solver states."""
from pathlib import Path
import datetime,json,shutil
R=Path(__file__).resolve().parent
now=datetime.datetime.now().astimezone();suffix=now.strftime('%Y%m%d_%H%M%S')
def read(p):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
record={'updated_at':now.isoformat(),'status':'completed','main':str(R.parent/'dashboard.html'),'research':str(R.parent/'professor_dashboard.html'),'features':['horizontal collapsible topic bars and nested tests','persistent open state and keyboard access','plain test names; attempt IDs in technical details','original schematic restored top-right on both views, below description on mobile','permanent operational computer/calculation section','read-only telemetry every20s with explicit machine and calculation-data freshness','mode-specific calm/wave/preparation metrics, GPU priority and concurrent preparation','case-matched scientific results, archived cohorts remain separate'],'qa':'accordion_ui_review_20261030.json','viewport_widths':[1920,1360,390],'print_pages':{'main_full_archive_landscape':39,'research_discussion':20},'campaign_paused':(R/'STOP_ALL').exists(),'solver_launched':False,'separate_HF_session':'Untouched as explicitly instructed','monitor':read(R/'dashboard_status_monitor.lock'),'local_balance_review':'professor_r14_local_balance_review.json','next_calculation_recommendation':'Reporting-only replay .500 to .630 with unchanged R14 settings, outlet face flux/alpha/pressure and last-two-column per-inner diagnostics. Requires explicit user resume; no new numerical-control change is yet supported.'}
(R/'dashboard_reorganization_20261030.json').write_text(json.dumps(record,indent=2),encoding='utf8')
p=R/'RESUME_AT_HOME.txt';shutil.copy2(p,R/('handover_history_'+suffix+'_before_dashboard.txt'))
header='DASHBOARDS REORGANIZED; CAMPAIGN STILL PAUSED — '+now.isoformat()+'\n'
header+='User requested dashboard work, not CFD restart. STOP_ALL remains; automation remains paused. Separate HF work untouched.\n'
header+='Both English views use horizontal topic bars and nested tests. Original simulation schematic restored top-right, mobile below.\n'
header+='Operational computer status is always outside collapsible sections; read-only monitor refreshes20s, page refresh30s, stale samples marked. Inspect dashboard_status_monitor.lock/state before any monitor relaunch. Monitor never starts solvers.\n'
header+='QA1920/1360/390 and print passed; see accordion_ui_review_20261030.json and dashboard_reorganization_20261030.json.\n'
header+='Saved R14 spatial analysis now COMPLETE: professor_r14_local_balance_review.json. At .618s two interface cells .1m from outlet contribute99.9132% of net water residual; CSV sums calibrate native values. Location proved, cause not proved.\n'
header+='Proposed next short calculation is reporting-only .500→.630 with unchanged R14 settings plus outlet-face and last-two-column iteration diagnostics. No solver launched and no guard/threshold changed.\n\n'
p.write_text(header+p.read_text(encoding='utf-8'),encoding='utf8')
for name in ('mesh_selection_plan.json','overnight_plan_20261029.json','wave_numerical_review_current.json'):
 p=R/name
 if not p.exists():continue
 shutil.copy2(p,R/(p.stem+'_before_dashboard_'+suffix+'.json'));d=read(p)
 d['dashboard_reorganization']={'updated_at':now.isoformat(),'record':'dashboard_reorganization_20261030.json','solver_restart_authorized':False}
 if name=='wave_numerical_review_current.json':d['post_pause_spatial_review']={'file':'professor_r14_local_balance_review.json','status':'localization_complete_cause_not_established','next_recommended':record['next_calculation_recommendation']}
 p.write_text(json.dumps(d,indent=2),encoding='utf8')
print(json.dumps({'record':'dashboard_reorganization_20261030.json','campaign_paused':record['campaign_paused'],'solver_launched':False}))
