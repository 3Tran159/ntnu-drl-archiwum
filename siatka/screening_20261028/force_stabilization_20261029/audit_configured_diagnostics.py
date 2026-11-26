import csv,json,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;T=R/'configured_mesh_20261029'
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
def mon(p):
 with p.open(encoding='utf-8-sig') as f:
  a=csv.reader(f);next(a);return {int(float(x[0])):float(x[1]) for x in a}
def stats(a):
 a=sorted(a);return {'median':statistics.median(a),'p95':a[math.ceil(.95*len(a))-1],'max':max(a),'n':len(a)} if a else None
out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':[]}
for rp in sorted(T.glob('*/configured_result.json')):
 short=rp.parent.name;inner=10
 p=T/short;r=json.loads((p/'configured_result.json').read_text());lo,hi=r['window'];h=[x for x in rows(p/'history.csv') if lo+1e-8<x['physical_time_s']<=hi+1e-8]
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
 a['vof_substeps']=sorted(set(int(x['VOF_substeps']) for x in rows(p/'vof_substeps.csv')));budget=rows(p/'conservation.csv');err=[];inlet=[]
 for i in range(2,len(budget)):
  x=budget[i]
  if not lo+1e-8<x['time_s']<=hi+1e-8:continue
  dt=x['time_s']-budget[i-1]['time_s'];res=(3*x['mass_kg']-4*budget[i-1]['mass_kg']+budget[i-2]['mass_kg'])/(2*dt)+x['net_outward_mass_kg_s']
  if x['inward_mass_kg_s']>0:err.append(100*abs(res)/x['inward_mass_kg_s'])
 a['BDF2_mass_budget_abs_pct_of_inlet']=stats(err)
 a['pressure_viscous_sum_max_error_N']=max(abs(x['Fx_slice_N']-x['pressure_drag_N']-x['viscous_drag_N']) for x in h)
 a['max_speed_all_history_m_s']=max(x['max_velocity_m_s'] for x in rows(p/'history.csv'))
 foil=rows(p/'foil_fields.csv');a['wall_yplus_max']=max(x['Wall Y+'] for x in foil)
 out['cases'].append(a)
(R/'configured_mesh_diagnostic_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'cases':[{'id':a['id'],'steps':a['steps'],'fields_all_finite':a['fields_all_finite'],'drag_inner_max_pct':a['monitors']['Fx_half_Monitor']['half_iterations_change_pct']['max'],'lift_inner_max_pct':a['monitors']['Fz_half_Monitor']['half_iterations_change_pct']['max'],'mass_BDF2_max_pct':a['BDF2_mass_budget_abs_pct_of_inlet']['max'],'wall_yplus_max':a['wall_yplus_max']} for a in out['cases']]},indent=2))
