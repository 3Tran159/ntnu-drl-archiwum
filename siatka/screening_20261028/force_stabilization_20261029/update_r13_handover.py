from pathlib import Path
from datetime import datetime
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp();tag=datetime.now().strftime('%Y%m%d_%H%M%S')
old=R/'RESUME_AT_HOME.txt';(R/f'handover_history_{tag}.txt').write_text(old.read_text(),encoding='utf-8')
old.write_text((R/'handover_r13_candidate.txt').read_text(),encoding='utf-8')
state=e.read(R/'wave_propagation_state.json',{})
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json','wave_numerical_review_current.json']:
 p=R/name;d=e.read(p,{})
 e.write(R/f'{p.stem}_history_{tag}.json',d)
 d['updated_at']=now;d['current_wave']=state;d['current_wave_snapshot']=state
 d['latest_execution']='Calm M09 supported; M10 paired inputs ready. R12 native-per-inner/AMG trace complete, failed mass gate; R13 only VOF tolerance .1 to .001 probe active; no wave force admission.'
 d['next_diagnostic']='Read actual R13 status; after completion run analyze_wave_vof_tolerance_r13.py and review achieved linear targets, native/BDF2 balance, gauge change, cost. No longer trial before scientific gate.'
 if name=='wave_numerical_review_current.json':
  d['status']='R12_linear_stopping_identified_R13_single_control_probe_active';d['R12']=e.read(R/'wave_linear_trace_r12_review.json',{});d['R11']=e.read(R/'wave_inner40_phase_probe_r11_review.json',{})
 if name=='overnight_plan_20261029.json':
  d['execution']=d['latest_execution'];d['near_hour']=[dict(stage='Current',action=d['next_diagnostic'])]
  d['elapsed_since_plan_hours']=(datetime.now().astimezone()-datetime.fromisoformat(d['created_at'])).total_seconds()/3600
 e.write(p,d)
print('Handover and four plans updated; histories preserved. Current state: '+state.get('status','unknown'))
