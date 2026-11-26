from pathlib import Path
import csv,json,statistics,datetime
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
import wave_cycle_dashboard_panel as ui
s=json.loads((R/'wave_foil_run_state.json').read_text());C=Path(s['directory'])
assert C.name=='W01a_W20L4_M10_inlet_fullheight_restart_r3'
h=list(csv.DictReader((C/'history.csv').open()));g=list(csv.DictReader((C/'gauges.csv').open()))
t=float(h[-1]['time_s']);T=float(json.loads((C/'wave_activation.json').read_text())['wave_period_s']);c=20/T
inlet=[r for r in g if float(r['x_m'])==-34 and float(r['time_s'])<T*.5]
crest=max(inlet,key=lambda r:float(r['eta_actual_m']))
ct=float(crest['time_s']);eta=float(crest['eta_actual_m'])
cost=ui._recent_cost(C,.001);speed=cost['median_s_per_step']/.001
targets={'crest_travel_from_minus34':ct+34/c,'phase_travel_from_inlet_only':35/c,'phase_travel_from_generation_zone_end':15/c}
d={'at':datetime.datetime.now().astimezone().isoformat(),'case':C.name,'current_time_s':t,'period_s':T,'phase_speed_m_s':c,'observed_near_inlet_crest':{'gauge_x_m':-34,'time_s':ct,'elevation_m':eta,'analytic_same_time_m':float(crest['eta_analytic_m'])},'timing':cost,'estimated_targets':{k:{'simulation_time_s':v,'remaining_simulation_s':max(0,v-t),'remaining_wall_minutes':max(0,v-t)*speed/60,'wall_range_minutes':[max(0,v-t)*cost[q]/.001/60 for q in ['p20_s_per_step','p80_s_per_step']]} for k,v in targets.items()},'arrival_measured_at_foil':False,'caveat':'Phase travel estimates only. Distributed inlet forcing overx[-35,-15] can create earlier disturbances. First coherent near-inlet crest trackedby single gauge thenextrapolated, not yet measured atfoil. No cycle-analysis origin assigned.'}
(R/'w01a_first_crest_arrival_estimate.json').write_text(json.dumps(d,indent=2))
print(json.dumps(d))
