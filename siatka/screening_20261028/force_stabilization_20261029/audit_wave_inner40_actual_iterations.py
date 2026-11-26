from pathlib import Path
import re,json
import run_until_settled as e
R=Path(__file__).resolve().parent;A=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_inner40phaseBudget_dt1ms_r11')
rows=[];pending=None
for line in (A/'star.log').read_text(errors='replace').splitlines():
 m=re.search(r'^TimeStep\s+(\d+): Time\s+(\S+)',line)
 if m:pending=(int(m[1]),float(m[2]));continue
 if pending:
  m=re.match(r'^\s+(\d+)\s+[-+0-9.]+e[-+]\d+',line,re.I)
  if m:rows.append(dict(step=pending[0],time_s=pending[1],cumulative_iterations=int(m[1])));pending=None
diff=[b['cumulative_iterations']-a['cumulative_iterations'] for a,b in zip(rows,rows[1:]) if b['step']==a['step']+1]
out=dict(updated_at=e.stamp(),partial=True,completed_physical_steps_in_log=len(rows),last_time_s=rows[-1]['time_s'] if rows else None,observed_inner_iterations_per_step_min=min(diff) if diff else None,observed_inner_iterations_per_step_max=max(diff) if diff else None,steps_not_40=sum(x!=40 for x in diff),method='Differences between final cumulative solver iteration counters printed immediately after consecutive TimeStep headers; not assumed from configured maximum.',report='Native phase-error reports currently sampled perphysicalstep; inner native-phase monitors andAMGverboseoutput requirefreshdiagnosticcopy.')
e.write(R/'wave_inner40_actual_iterations_audit.json',out);print(json.dumps(out))
