from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parent;B=R.parent;D=R/'wave_arrival_ui_qa_20261030'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
a=read(D/'integrated_review.json');states=read(D/'state_test_review.json');clear=read(D/'case_clear_review.json');raw=read(D/'raw_history_preservation_review.json');pr=read(D/'print_review.json')
assert len(a['rows'])==6
for row in a['rows']:
 assert row['firstCD'][0]>=.2-1e-10 and not row['overflow'] and not row['errors'] and not row['svgNonfinite'] and not row['catalog']['bad']
 for sc in row['scrolls']:
  if sc['class']=='wcp-plot-scroll':assert sc['remaining']<=1
assert a['live']['after']['current_time_s']>a['live']['before']['current_time_s']
assert a['live']['after']['simulation_remaining_s']<a['live']['before']['simulation_remaining_s']
assert states['status']=='PASS' and clear['status']=='PASS'
assert raw['files']['startup_history.csv']['samples_before_display_start']==40
parity={}
for name in ('dashboard.html','professor_dashboard.html'):
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 orig=sha(B/name);copy=sha(B/'dashboard_work_20261030'/name);assert orig==copy
 parity[name]=orig
result={'status':'PASS_BOUNDED_UI_REVIEW','created_at':datetime.datetime.now().astimezone().isoformat(),'case':a['rows'][0]['case'],'scope':'First-crest live forecast, display starting at t=.2, integrated catalog wrapping; not physical wave acceptance.','surfaces':['operational','professor'],'widths':[1920,1360,390],'checks':{'live':'5-second poll updates actual simulated time and remaining simulation seconds. Real compute estimate uses recent current-case step costs.','states':list(states['tests']),'expiry':'Predicted threshold passed does not assert measured arrival or enable cycle acceptance.','case_isolation':'Wrong case/unavailable clear target, remaining, wall, current and note.','plot_display':'All displayed series begin at .20000000000000015 s; initial spike excluded from axis scaling. Mobile Follow live reaches latest right edge.','raw_history':'All40 startup rows remain from.0005s; main CSV retains180 pre-.2s samples. No history was rewritten.','layout':'No JS errors, page overflow, nonfinite plot paths or catalog cell text-bound violations in six combinations.','visual':'Desktop/mobile countdown and catalog screenshots reviewed. Main print pages5/7 and professor2/4 reviewed; no text collision or cut table rows.','actions':'Read-only browser GET/HEAD only; no CFD, HTTP-service restart, solver or lock action.'},'print':pr,'parity':parity,'artifacts':str(D),'screenshots':['operational_1360_arrival.png','operational_390_arrival.png','professor_390_catalog.png','operational_print_page_5.png','professor_print_page_4.png']}
(R/'wave_arrival_ui_review_20261030.json').write_text(json.dumps(result,indent=2),encoding='utf8')
old=read(R/'w01a_fullheight_restart_live_ui_review.json');old['remaining']='None; catalog collision fixed and integrated wrapping visually verified in wave_arrival_ui_review_20261030.json.';old['checks']['catalog']='Fixed: scoped wrapping and mobile cards. Six-view text Range containment checks and desktop/mobile/print visual review pass.'
(R/'w01a_fullheight_restart_live_ui_review.json').write_text(json.dumps(old,indent=2),encoding='utf8')
print(json.dumps({'status':result['status'],'review':str(R/'wave_arrival_ui_review_20261030.json'),'parity':parity}))
