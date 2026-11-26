from pathlib import Path
import json,csv,html,shutil
E='C0_SPEED_DOWN_20261103'
def publish(h,view,base,st,review):
 rec=st.get('active');jobs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]
 if not rec or rec.get('experiment_id')!=E:rec=max(jobs,key=lambda r:r.get('ended_at',''),default=None)
 data=dict(experiment_id=E,solver_state=base['solver_state'],operation=base['solver_state'],CPU=8,GPU=False,flap_deg=0,previous_failures_blocked=True,scientific_approved=False)
 if rec:
  out=Path(rec['output']);data.update(output=str(out),job=rec['id'],result=rec.get('macro_status'))
  p=out/'history.csv'
  if p.exists():
   with p.open() as f:rows=list(csv.DictReader(f))
   if rows:data.update(latest=rows[-1],steps=len(rows))
   shutil.copyfile(p,h/'C0_SPEED_DOWN_HISTORY.csv')
  if (out/'pressure_zones.csv').exists():shutil.copyfile(out/'pressure_zones.csv',h/'C0_SPEED_DOWN_PRESSURE.csv')
  checkpoint=st.get('checkpoint_integrity',{}).get(str(out/'checkpoint.sim')) or st.get('checkpoint_integrity',{}).get(str(out/'error_checkpoint.sim'))
  if checkpoint:data['checkpoint']=checkpoint
 base.update(current_case_label='C0 0deg speed-down diagnostic',max_cpu_processes=8,operation=base['solver_state'],mesh_cells=333939,flow_frozen=False)
 base['actual_live_metrics']['operation']=base['solver_state'];view.update(operation=base['solver_state'],solver_state=base['solver_state'],c0_speeddown=data)
 p=h/'C0_SPEED_DOWN_STATUS.json';p.with_suffix('.json.tmp').write_text(json.dumps(data,indent=2));p.with_suffix('.json.tmp').replace(p)
def render(h,view,base,review):
 e=html.escape;txt='<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="30"><style>body{font:18px system-ui;max-width:900px;margin:30px auto;padding:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>'+e(base['solver_state'])+' — C0, klapka0°, redukcja U</h1><p>'+e(review['last_decision'])+'</p><p>8CPU, bez GPU. Poprzednie FAIL i pełny sweep pozostają zablokowane.</p><p><a href="C0_SPEED_DOWN_HISTORY.csv">Historia CSV</a> · <a href="C0_SPEED_DOWN_PRESSURE.csv">Ciśnienia CSV</a> · <a href="C0_SPEED_DOWN_STATUS.json">Status JSON</a></p><pre>'+e(json.dumps(view.get('c0_speeddown',{}),indent=2))+'</pre></html>'
 (h/'NIGHT_DASHBOARD.html').write_text(txt,encoding='utf8')
