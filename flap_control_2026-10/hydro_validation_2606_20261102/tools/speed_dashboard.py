import json,csv,html,shutil
from pathlib import Path
E='SPEED_SWEEP_PLUS2_20261103'
def publish_speed(h,view,base,st,review):
 jobs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]
 rec=st.get('active')
 if not rec or rec.get('experiment_id')!=E:rec=max(jobs,key=lambda x:x.get('ended_at',''),default=None)
 summary=dict(experiment_id=E,solver_state=base['solver_state'],operation=base['solver_state'],old_ramp_failed=True,training_approved=False,completed_speeds=[],pending_speeds=[10,12,14,16,18])
 if rec:
  out=Path(rec['output']);summary['output']=str(out)
  for name,key in [('sweep_progress.json','progress'),('convergence_latest.json','convergence'),('checkpoint_latest.json','checkpoint'),('status.json','result')]:
   try:summary[key]=json.loads((out/name).read_text())
   except (FileNotFoundError,json.JSONDecodeError):pass
  results=out/'static_results.csv'
  if results.exists():
   shutil.copyfile(results,h/'SPEED_SWEEP_STATIC_RESULTS.csv')
   with results.open() as f:summary['static_results']=list(csv.DictReader(f))
   summary['completed_speeds']=[int(r['U_m_s']) for r in summary['static_results']]
   summary['pending_speeds']=[u for u in [10,12,14,16,18] if u not in summary['completed_speeds']]
  if (out/'history.csv').exists():shutil.copyfile(out/'history.csv',h/'SPEED_SWEEP_HISTORY.csv')
  if (out/'pressure_zones.csv').exists():shutil.copyfile(out/'pressure_zones.csv',h/'SPEED_SWEEP_PRESSURE_HISTORY.csv')
  if (out/'static_pressure_results.csv').exists():shutil.copyfile(out/'static_pressure_results.csv',h/'SPEED_SWEEP_STATIC_PRESSURES.csv')
 if not st.get('active') and summary.get('result',{}).get('status')=='speed_sweep_complete':base['solver_state']='STOPPED';summary.update(solver_state='STOPPED',operation='STOPPED')
 base.update(current_case_label='Fixed+2 velocity sweep',mesh_cells=333939,max_cpu_processes=8,operation=base['solver_state'],flow_solution_approved=False)
 base['actual_live_metrics']['operation']=base['solver_state'];view.update(operation=base['solver_state'],solver_state=base['solver_state'],speed_sweep=summary)
 (h/'SPEED_SWEEP_STATUS.json.tmp').write_text(json.dumps(summary,indent=2));(h/'SPEED_SWEEP_STATUS.json.tmp').replace(h/'SPEED_SWEEP_STATUS.json')
def render_speed(h,view,base,review):
 e=html.escape;summary=view.get('speed_sweep',{})
 text='<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30"><style>body{font:17px system-ui;max-width:950px;margin:24px auto;padding:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>'+e(base['solver_state'])+' — stała klapka +2°</h1><p>10 → 12 → 14 → 16 → 18 m/s. Maks.8CPU, bez GPU. Rampa pozostaje FAIL. Wyniki statyczne tylko po stabilizacji.</p><p>'+e(review.get('last_decision',''))+'</p><p><a href="SPEED_SWEEP_STATIC_RESULTS.csv">Wyniki ustalone CSV</a> · <a href="SPEED_SWEEP_HISTORY.csv">Historia rozruchu CSV</a> · <a href="SPEED_SWEEP_STATUS.json">Status JSON</a></p><pre>'+e(json.dumps(summary,indent=2,ensure_ascii=False))+'</pre></html>'
 (h/'NIGHT_DASHBOARD.html').write_text(text,encoding='utf8')
