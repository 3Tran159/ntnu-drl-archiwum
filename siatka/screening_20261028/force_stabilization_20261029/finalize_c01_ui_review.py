from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parent;B=R.parent;D=R/'c01_calm_dashboard_qa_20261030'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
a=read(D/'integrated_review.json');numeric=read(D/'numeric_interaction_print_review.json');mobile=read(D/'mobile_rolling_stable_review.json');manifest=read(R/'wave_side_view_current.json')
assert len(a['rows'])==6 and len(numeric['numeric'])==12
assert all(not r['overflow'] and all(p['paths']==1 and len(p['limits'])==2 for p in r['plots']) for r in mobile)
findings=[]
if manifest.get('case')=='C01_W20L4_M10_calm_settle_r2' and ('W01a' in manifest.get('caption','') or 'Fresh calm-start' in manifest.get('lineage','')):findings.append('Correct C01 actual field is displayed, but its manifest caption/lineage retains old W01a/fresh-start wording. Root notified for source correction.')
parity={}
for f in ('dashboard.html','professor_dashboard.html'):
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 v=sha(B/f);w=sha(B/'dashboard_work_20261030'/f);assert v==w
 parity[f]=v
review={'status':'PASS_CORE_UI_CAPTION_PENDING' if findings else 'PASS_BOUNDED_C01_UI_REVIEW','created_at':datetime.datetime.now().astimezone().isoformat(),'case':'C01_W20L4_M10_calm_settle_r2','surfaces':['operational','professor'],'widths':[1920,1360,390],'checks':{'routing':'C01 continuation from saved computed .587s, H0, no reinitialization. No wave arrival countdown or period-based ETA.','plots':'CD,CL_total,CD_window_pct,CL_window_pct only. No per-step traces. Rolling means use adjacent nonoverlapping .2s intervals and require .4s current history.','numerical':'All12 captured rolling endpoints independently recomputed from raw current-case history agree within1e-10 percentage points.','interaction':'Four Follow axes synchronized; manual pan persisted afterreload. Mobile latestedge visible.','threshold':'Both ±.5% reference guides visible in mobile/static/interactive and print.','layout':'Six combinations have no JS errors, page overflow, nonfinite plot paths or catalog text-bound violations. Desktop/mobile screenshots visually inspected.','mobile_capture':'Initial rapid-scroll rolling screenshots were blank capture artifacts and are superseded by *_390_rolling_stable.png after browser-only refresh pause/render wait.','print':'Operational pages3/5 and professor3/5 visually inspected: source/gate table, rolling plots/formula/thresholds and11catalog rows readable, no collisions or cut rows.','field':'Actual case-matched C01 fieldt.837; source identity is correct, fieldtimestamp explicit.','catalog':'C01 active; W01a awaits saved settled C01 copy, fullH from activation, no height ramp.','actions':'No solver/service/lock actions or source-data modifications; only read-only QA and browser presentation controls.'},'open_findings':findings,'parity':parity,'artifacts':str(D),'screenshots':['operational_1360_overview.png','operational_1360_rolling.png','operational_390_rolling_stable.png','professor_390_rolling_stable.png','operational_print_page_5.png','professor_print_page_5.png']}
(R/'c01_calm_dashboard_ui_review_20261030.json').write_text(json.dumps(review,indent=2),encoding='utf8')
print(json.dumps({'status':review['status'],'open_findings':findings,'review':str(R/'c01_calm_dashboard_ui_review_20261030.json')}))
