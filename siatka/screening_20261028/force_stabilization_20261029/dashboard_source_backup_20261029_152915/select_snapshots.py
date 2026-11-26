import csv,json
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def csvrows(p):
 with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
selected={}
for m in ['M03','M02','M04','M05']:
 for j in read(R/'queue.json',[]):
  if not j['id'].startswith(m+'_'):continue
  out=R/j['id'];done=read(out/'completed.json',{});accept=read(out/'acceptance.json',{})
  if done.get('status')!='stabilized' and accept.get('status')!='settled':continue
  if not (out/'velocity_vectors.csv').exists() or not (out/'foil_fields.csv').exists():continue
  last=csvrows(out/'history.csv')[-1];t=float(last['physical_time_s'])
  assert abs(t-float(done['time_s']))<1e-8
  selected[m]={'status':'Settled','time_s':t,'folder':str(out),'wall':str(out/'foil_fields.csv'),'velocity':str(out/'velocity_vectors.csv'),'history':str(out/'history.csv'),'pressure_drag_N':float(last['pressure_drag_N']),'viscous_drag_N':float(last['viscous_drag_N']),'mean_yplus':float(last['mean_yplus'])}
 if m not in selected and m in ['M03','M02']:
  out=Q/(m+'_GPU')/'F18_dt1000us_long';last=csvrows(out/'history.csv')[-1]
  selected[m]={'status':'Startup','time_s':.2,'folder':str(out),'wall':str(out/'foil_final_fields.csv'),'velocity':str(R/(m+'_pilot_post')/'velocity_vectors.csv'),'history':str(out/'history.csv'),'pressure_drag_N':{'M03':55.1264,'M02':95.34209}[m],'mean_yplus':float(last['foil_mean_yplus'])}
(R/'selected_snapshots.json').write_text(json.dumps(selected,indent=2))
print(json.dumps({m:{k:v[k] for k in ['status','time_s']} for m,v in selected.items()}))
