import csv,json,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;T=R/'temporal_order_20261029'
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
def mon(p):
 with p.open(encoding='utf-8-sig') as f:
  a=csv.reader(f);next(a);return {int(float(x[0])):float(x[1]) for x in a}
def stats(a):
 a=sorted(a);return {'median':statistics.median(a),'p95':a[math.ceil(.95*len(a))-1],'max':max(a),'n':len(a)} if a else None
out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':[]}
for short,inner in [('T02_M04_SO_dt1ms_r1',20),('T04_M04_SO_dt1ms_inner10_r1',10)]:
 p=T/short;r=json.loads((p/'experiment_result.json').read_text());lo,hi=r['comparison_window'];h=[x for x in rows(p/'history.csv') if lo+1e-8<x['physical_time_s']<=hi+1e-8]
 a={'id':short,'window':[lo,hi],'steps':len(h),'all_history_finite':all(math.isfinite(v) for x in h for v in x.values()),'monitors':{}}
 for name in ['Fx_half_Monitor','Fz_half_Monitor','Continuity','X-momentum','Y-momentum','Z-momentum','Tke','Sdr','water']:
  m=mon(p/('monitor_'+name+'.csv'));end=[];half=[];nonfinite=0;missing=0
  for x in h:
   stop=int(x['iteration']);mid=stop-inner//2
   if stop not in m or mid not in m:missing+=1;continue
   if not math.isfinite(m[stop]) or not math.isfinite(m[mid]):nonfinite+=1;continue
   end.append(m[stop])
   if abs(m[stop])>1e-15:half.append(100*abs(m[stop]-m[mid])/abs(m[stop]))
  a['monitors'][name]={'end':stats(end),'half_iterations_change_pct':stats(half) if name.endswith('_Monitor') else None,'missing':missing,'nonfinite':nonfinite}
  if name.endswith('_Monitor'):a['monitors'][name]['independent_crosscheck_max_N']=max(abs(m[int(x['iteration'])]-x['Fx_slice_N' if name.startswith('Fx') else 'Fz_slice_N']) for x in h)
 fluid=rows(p/'fluid_fields.csv');alpha=[x['Volume Fraction of water'] for x in fluid];a['phase_bounds']=[min(alpha),max(alpha)];a['fields_all_finite']=all(math.isfinite(v) for x in fluid for v in x.values());a['cells']=len(fluid)
 a['vof_substeps']=sorted(set(int(x['VOF_substeps']) for x in rows(p/'vof_substeps.csv')));out['cases'].append(a)
(R/'professor_inner_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
