from pathlib import Path
import json,datetime,hashlib
R=Path(__file__).resolve().parent;B=R.parent;D=R/'w01a_native_fields_qa_20261030'
qa=json.loads((D/'qa.json').read_text());pr=json.loads((D/'print_review.json').read_text());v=json.loads((R/'wave_vorticity_current.json').read_text());alpha=json.loads((R/'wave_side_view_current.json').read_text())
assert len(qa['rows'])==6
for row in qa['rows']:
 assert row['case']=='W01a_W20L4_M10_calm_start_r1' and not row['overflow'] and not row['errors']
 assert all(im['loaded'] for im in row['images']) and len(row['images'])==2
 assert row['eta']==0 and row['wave_phase']==0 and row['bars']==3
 assert 'saved' in row['status'].lower()
 if row['width']==390:assert row['keyboard_toggle'] is True
assert all(len(pages)==1 and pages[0]['summary'] and pages[0]['caption'] for pages in pr.values())
parity={}
for name in ('dashboard.html','professor_dashboard.html'):
 vals=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (B/name,B/'dashboard_work_20261030'/name)]
 parity[name]={'original':vals[0],'copy':vals[1],'equal':vals[0]==vals[1]}
assert all(x['equal'] for x in parity.values())
report={'status':'PASS','updated_at':datetime.datetime.now().astimezone().isoformat(),'case':'W01a_W20L4_M10_calm_start_r1','user_override':'Activate inlet wave without waiting for calm force convergence; current startup fields saved and wave activation pending','surfaces':['operational','professor'],'widths':[1920,1360,390],'checks':{'current_case_only':True,'old_r2_history_cleared_from_live_panel':True,'rich_stage_strip':'Startup → Inlet wave ramp → Wave arrival → Repeating cycles','progress_bars':3,'force_settling_gate_removed':True,'phase_clock_pending':True,'eta_pending_activation':True,'calm_diagnostics_optional':True,'loaded_actual_field_images_per_panel':2,'keyboard_vorticity_toggle_pass':True,'page_overflow':False,'js_errors':0,'print_heading_image_caption_same_page':True,'source_copy_parity':parity},'fields':{'free_surface_time_s':alpha['field_time_s'],'vorticity_time_s':v['field_time_s'],'vorticity_source':'Native STAR VorticityVector component1; no velocity-gradient reconstruction','views':v['views'],'exact_foil_triangle_intersection_mask':True,'source_checkpoint_audit_zero_steps':True,'accepted':False},'local_service':{'http_pid':39700,'restarted_only_http_from':26648,'legacy_full_domain_wave_presets_disabled':True,'C01_presets_allowed':True,'solver_actions':0,'STOP_or_schedule_actions':0},'evidence':{'screens_and_DOM':str(D/'qa.json'),'print':str(D/'print_review.json'),'wide':str(D/'operational_1920_panel.png'),'mobile':str(D/'professor_390_panel.png'),'vorticity_print':str(D/'professor_vorticity_print_4.png'),'vorticity_provenance':v['provenance_path'],'free_surface_provenance':alpha['provenance_path']},'limits':['Both images are actual saved fields with different explicit timestamps; neither is claimed to be current solver time.','Display-clipping percentages are by saved cell centres within each view, not physical area.','The analytical ramp API audit failed separately; these actual calm fields do not validate inlet-wave propagation.','Next active inlet-wave case needs exact onset/ramp/arrival/analysis_origin metadata before wave-cycle binding.']}
(R/'w01a_native_fields_ui_review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
old=R/'w01a_dashboard_transition_ui_review.json';record=json.loads(old.read_text());record['superseded_by']='w01a_native_fields_ui_review.json';old.write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps({'status':'PASS','review':str(R/'w01a_native_fields_ui_review.json'),'free_surface_time_s':alpha['field_time_s'],'native_vorticity_time_s':v['field_time_s'],'print':pr,'parity':parity}))
