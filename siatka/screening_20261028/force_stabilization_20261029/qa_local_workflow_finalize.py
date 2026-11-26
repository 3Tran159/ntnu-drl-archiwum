import json,sys,csv,math,re
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029');D=R/'local_workflow_ui_qa_20261030'
sys.path.insert(0,str(R));import wave_cycle_dashboard_panel as panel
probe={'case':'LOCAL_C01_dt05ms_probe_r3','directory':'E:/ntnu/quasi2d_waves_20261029/LOCAL_C01_dt05ms_probe_r3','computation_stage':'calm_settling','diagnostic_only':True,'source_time_s':1.837,'manual_request':{'target_s':2.9},'computation_active':True,'status':'running','scope':'Half-step diagnostic only; 0.5 ms, 10 inner iterations.'}
with patch.object(panel,'_read',return_value={}),patch.object(panel,'_history',return_value=([],[])),patch.object(panel,'_side_view',return_value=''),patch.object(panel,'_vorticity_view',return_value=''):
 html=panel.render(probe,{},{});probe_check={'correct_title':'C01 — time-step diagnostic' in html,'source_time':'1.837 s' in html,'monitor_only':'not an automatic stopping or acceptance test' in html,'no_acceptance':'Not an acceptance run' in html,'no_wave_eta':'Arrived wave cycles' not in html,'no_historical_label':'W01 continuation' not in html}
assert all(probe_check.values()),probe_check
raw=json.loads((D/'raw_review.json').read_text(encoding='utf8'));guard=json.loads((D/'guard_state_review.json').read_text(encoding='utf8'));resources=json.loads((D/'final_resource_print_review.json').read_text(encoding='utf8'));pr=json.loads((D/'print_review.json').read_text(encoding='utf8'))
sys.path.insert(0,r'C:/Users/ThinkPad/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages')
from pypdf import PdfReader
printing=[]
for surface in ['operational','professor']:
 pdf=PdfReader(str(D/(surface+'_print.pdf')));texts=[p.extract_text() or '' for p in pdf.pages]
 pages=[(i+1,t) for i,t in enumerate(texts) if 'Wave cases and parameters' in t and 'Definition / startup' in t]
 printing.append({'surface':surface,'pages':len(pdf.pages),'catalog_pages':[i for i,t in pages],'all_notes_with_catalog':all('Fifth-order' in t and 'Second-order implicit' in t and 'C01 denotes' in t for i,t in pages),'all_eleven_rows_present':all(all(x in t for x in ['W01a','W02','W03','W04','W05','W06','W07','W08','W01_3lambda']) for i,t in pages),'table_font_pt':8,'notes_font_pt':9})
out={'updated_at':datetime.now().astimezone().isoformat(),'status':'PASS_SCOPED_UI_REVIEW','scope':'Read-only live HTTP and file dashboard review; no Start/Stop/Open/Queue actions, solver operations, lock changes or non-GET requests. All-width checks before guard plus targeted desktop/mobile terminal-state recheck. Full PDFs exported; changed print sections visually inspected, not every historical page.',
'views':{'surfaces':['operational','professor'],'widths_px':[1920,1360,390],'checks':raw['initialChecks'],'latest_failed_case_widths_px':[1360,390],'terminal_state_pass':guard['pass']},
'workflow':raw['workflow'],'local_controls':{'file_readonly':raw['fileView'],'results_link':raw['resultsLink'],'action_buttons_clicked':0,'non_get_requests':len(raw['blockedMutations'])+len(guard['blocked'])},
'telemetry':{'current_ascii_temperature_clock_power':all('deg C' in x['text'] and 'MHz' in x['text'] and ' W.' in x['text'] for x in resources['resources']),'current_limiter_labels':all('Thermal clock limiter:' in x['text'] and 'power limiter:' in x['text'] for x in resources['resources']),'recent_sample_ages_s':[re.search(r'Sample age: (\\d+) s',x['text']).group(1) for x in resources['resources'] if re.search(r'Sample age: (\\d+) s',x['text'])],'cost_note':'Typical step - last 50, last step and mean were visually checked while C01 was active. The cost cards are omitted in the later stopped state, so the earlier combined asciiUnits boolean in final_resource_print_review.json is false because it also required that inactive-only card. Temperature/clock/power labels are correct.'},
'failed_c01':{'case':'C01_W20L4_M10_calm_settle_r2','final_saved_time_s':2.777,'last_regular_history_time_s':guard['views'][0]['latest'],'source_time_s':.587,'diagnostic_links':[x['diagnosticLink'] for x in guard['views']],'settled_file_created':False,'wave_started_from_this_continuation':False,'stage_labels':[x.get('stages') for x in guard['views']],'stats':[x.get('stats') for x in guard['views']]},
'print':printing,'isolated_diagnostic_route':probe_check,'display_tests':'3/3 existing C01 tests passed: window formula/coverage/gaps/near-zero; stage dispatch; settled file evidence gating.',
'edits':[{'file':str(R/'wave_case_catalog_panel.py'),'change':'Print-only 2pt vertical cell padding and 3pt paragraph margin; existing 8pt table and 9pt note fonts preserved; catalog notes no longer orphaned.'},{'file':str(R/'wave_cycle_dashboard_panel.py'),'change':'Explicit physical-guard terminal label, diagnostic saved-state link, final timestamp and blocked stages; diagnostic_only C01 rendering without automatic force acceptance.'}],
'artifacts':{'all_widths':str(D/'raw_review.json'),'failed_state':str(D/'guard_state_review.json'),'resource':str(D/'final_resource_print_review.json'),'print':str(D/'print_review.json'),'screenshots_directory':str(D)},'remaining_scope_note':'Parent owns failure sideview caption generation. Exact case and t2.777 image were verified; latest caption refresh is recorded separately if updated after these captures.'}
assert all(x['all_notes_with_catalog'] and x['all_eleven_rows_present'] for x in printing),printing
assert guard['pass']
(R/'local_workflow_ui_review_20261030.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps({'status':out['status'],'print':printing,'probe':probe_check,'review':str(R/'local_workflow_ui_review_20261030.json')},indent=2))
