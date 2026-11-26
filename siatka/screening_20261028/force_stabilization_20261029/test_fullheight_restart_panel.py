from pathlib import Path
import json,math,datetime,py_compile
R=Path(__file__).resolve().parent;p=R/'wave_cycle_dashboard_panel.py';s=p.read_text(encoding='utf8')
s=s.replace("+' The interior flow was not globally reinitialized. Calm-force convergence is not required before activation.</p>'", "+(' The interior starts from calm zero-time fields; there is no full-domain wave initialization.' if fresh else ' The interior flow was not globally reinitialized.')+' Calm-force convergence is not required before activation.</p>'",1)
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True)
import wave_cycle_dashboard_panel as panel
case='W01a_W20L4_M10_inlet_fullheight_restart_r3'
state={'case':case,'directory':'E:/ntnu/quasi2d_waves_20261029/'+case,'source_time_s':0,'computation_stage':'inlet_wave_loading','computation_active':True,'status':'loading','progress':{'time_s':0}}
a=panel.render(state,{},{});assert '<h2>W01a — inlet-generated wave</h2>' in a
assert 'Fresh calculation from t = 0' in a and 'Full-height inlet · no ramp' in a
assert 'Ramp duration' not in a and 'to the end of the inlet ramp' not in a and '0.587' not in a and '0.168' not in a
assert '50 inner iterations' in a and 'class="wcp-cycle-comparison"' not in a
assert 'data:image' not in a
state['computation_stage']='inlet_wave_full_amplitude';state['progress']={'time_s':.0005};state['activation']={'activation_time_s':0,'ramp_duration_s':0,'ramp_end_time_s':0,'height_mode':'constant_full_height_from_activation','height_m':.5,'wave_period_s':.8472673,'planning_full_height_period_s':.8472673,'analysis_origin_s':None}
a=panel.render(state,{},{});assert '0.500000 m' in a and 'measuring arrival' in a
assert 'class="wcp-cycle-comparison"' not in a and '0.587' not in a
rows=[(i/100,1+math.sin(2*math.pi*i/100),2+math.cos(2*math.pi*i/100),None,None) for i in range(1421)]
shifted=panel._cycle_display(rows,{'wave_clock_origin_s':10,'nominal_history_interval_s':.01},1)
assert [x['cycle'] for x in shifted['cycles']]==[1,2,3,4]
assert abs(shifted['cycles'][0]['start_s']-10)<1e-10 and abs(shifted['partial']['start_s']-14)<1e-10
base=panel._cycle_display(rows[:421],{'wave_clock_origin_s':0,'nominal_history_interval_s':.01},1)
assert [x['cycle'] for x in base['cycles']]==[1,2,3,4] and base['cycles'][0]['start_s']==0
review={'status':'PASS_UI_PREFLIGHT_NOT_LAUNCH','at':datetime.datetime.now().astimezone().isoformat(),'case':case,'loading_and_first_step_labels_pass':True,'old_trial_series_or_field_binding_absent':True,'no_height_ramp_or_ramp_eta':True,'numerical_startup_declared':{'dt_s':.0005,'inner':50,'steps':40,'full_height_wave_from_first_step':True},'analysis_origin_display_test':{'origin_s':10,'complete_cycles':[1,2,3,4],'partial_start_s':14,'legacy_origin0_unchanged':True},'solver_actions':0,'actual_flow_validation':False}
(R/'w01a_fullheight_restart_ui_preflight.json').write_text(json.dumps(review,indent=2),encoding='utf8')
(R/'w01a_fullheight_restart_panel_preview.html').write_text('<html><meta name="viewport" content="width=device-width,initial-scale=1"><body>'+a+'</body></html>',encoding='utf8')
import build_manual_dashboard_copy as b;b.build()
print(json.dumps(review))
