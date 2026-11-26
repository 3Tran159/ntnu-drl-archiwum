import csv,datetime,json,statistics
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def rows(p):
 try:
  with p.open(newline='',encoding='utf-8-sig') as f:return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f) if all(v is not None and v!='' for v in r.values())]
 except (OSError,ValueError):return []
def summarize(data):
 if not data:return {}
 data=sorted({round(r['physical_time_s'],9):r for r in data}.values(),key=lambda r:r['physical_time_s'])
 last=data[-1];t=last['physical_time_s'];windows=[]
 for lo,hi in [(t-.4,t-.2),(t-.2,t)]:
  a=[r for r in data if lo+1e-8<r['physical_time_s']<=hi+1e-8]
  if len(a)<2 or a[-1]['physical_time_s']-a[0]['physical_time_s']<.198-1e-8:continue
  stats={'start':lo,'end':hi,'n':len(a)}
  for key in ['CD','CL_total','pressure_drag_N','viscous_drag_N']:
   if not all(key in r for r in a):continue
   vals=[r[key] for r in a];mean=statistics.mean(vals)
   stats[key]={'mean':mean,'rms_fluctuation':statistics.pstdev(vals),'range':max(vals)-min(vals),'drift_endpoints_pct':100*(vals[-1]-vals[0])/abs(mean) if mean else None}
  windows.append(stats)
 shifts={k:100*(windows[1][k]['mean']-windows[0][k]['mean'])/abs(windows[0][k]['mean']) for k in ['CD','CL_total']} if len(windows)==2 else {}
 stable=bool(shifts) and all(abs(x)<.5 for x in shifts.values())
 return {'rows':len(data),'last':last,'windows':windows,'window_mean_shift_pct':shifts,'settling_screen_pass':stable,'note':'Adjacent non-overlapping 0.2 s windows; mean changes <0.5%. RMS and endpoint drift are diagnostics; no extra confirmation window.'}
jobs=read(R/'queue.json',[]);status=read(R/'queue_state.json',{})
evidence={j['id']:summarize(rows(R/j['id']/'history.csv')) for j in jobs};meshes={}
for m in [c['id'] for c in read(R/'campaign_registry.json',{}).get('cases',[])]:
 data=rows(Q/(m+'_GPU')/'F18_dt1000us_long/history.csv')
 for j in jobs:
  if j['id'].startswith(m+'_'):data+=rows(R/j['id']/'history.csv')
 meshes[m]=summarize(data)
p=R/'live_summary.json';tmp=p.with_suffix('.tmp')
tmp.write_text(json.dumps({'updated_at':datetime.datetime.now().astimezone().isoformat(),'queue':status,'jobs':evidence,'meshes':meshes},indent=2),encoding='utf-8');tmp.replace(p)
