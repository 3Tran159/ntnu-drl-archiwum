from pathlib import Path
from datetime import datetime
import run_until_settled as e
R=Path(__file__).resolve().parent;now=e.stamp();tag=datetime.now().strftime('%Y%m%d_%H%M%S')
old=R/'RESUME_AT_HOME.txt';(R/f'handover_history_{tag}.txt').write_text(old.read_text(),encoding='utf-8')
old.write_text((R/'handover_r14_candidate.txt').read_text(),encoding='utf-8')
state=e.read(R/'wave_propagation_state.json',{})
for name in ['mesh_selection_plan.json','overnight_plan_20261029.json','wave24m_preparation_plan.json','wave_numerical_review_current.json']:
 p=R/name;d=e.read(p,{})
 e.write(R/f'{p.stem}_history_{tag}.json',d)
 d['updated_at']=now;d['current_wave']=state;d['current_wave_snapshot']=state
 d['latest_execution']='Calm M09 supported; M10 paired inputs ready. R12 trace complete; R13 tighterVOF achieved target but mass gate failed. R14 pressure-only tolerance .1 to .01 with calibrated spatial diagnostics active; no wave force admission.'
 d['next_diagnostic']='After actual R14 completion/source preservation run analyze_wave_pressure_tolerance_r14.py; inspect achieved linear targets and calibrated local_balance_t*.json/csv. If plateau persists, localize phase error; do not blindly add iterations or relax .01%.'
 if name=='wave_numerical_review_current.json':
  d['status']='R13_tighter_VOF_failed_mass_gate_R14_pressure_probe_active';d['R13']=e.read(R/'wave_vof_tolerance_r13_review.json',{})
 if name=='overnight_plan_20261029.json':
  d['execution']=d['latest_execution'];d['near_hour']=[dict(stage='Current',action=d['next_diagnostic'])]
  d['elapsed_since_plan_hours']=(datetime.now().astimezone()-datetime.fromisoformat(d['created_at'])).total_seconds()/3600
 e.write(p,d)
print('R14 handover and four plans updated; histories preserved.')
