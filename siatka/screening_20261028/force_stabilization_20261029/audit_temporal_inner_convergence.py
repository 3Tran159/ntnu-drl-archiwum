"""Compare saved inner monitors only; never modify or launch a simulation."""
import csv,json,math,statistics,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;T=R/'temporal_order_20261029'
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
def monitor(p):
 with p.open(encoding='utf-8-sig') as f:
  a=csv.reader(f);next(a);return {int(float(x[0])):float(x[1]) for x in a}
def stats(a):
 a=sorted(a)
 if not a:return None
 return {'n':len(a),'median':statistics.median(a),'p95':a[min(len(a)-1,math.ceil(.95*len(a))-1)],'max':max(a)}
out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':[],'method':'Only final comparison-window iterations from the independent per-step history. Older inherited NaNs are excluded by iteration identity, not silently replaced. Inner-force changes are diagnostic; normalized residuals are not a mass balance.','conservation_status':'Boundary mass/phase-flux plus accumulation budget is not recorded in these exports; must audit before declaring configuration fully verified.'}
for j in read(R/'temporal_validation_plan.json',{}).get('jobs',[]):
 p=T/j['id'];result=read(p/'experiment_result.json',{})
 if not result:continue
 h=rows(p/'history.csv');lo,hi=result['comparison_window'];h=[a for a in h if lo+1e-8<a['physical_time_s']<=hi+1e-8]
 keys=['Fx_half_Monitor','Fz_half_Monitor','Continuity','X-momentum','Y-momentum','Z-momentum','Tke','Sdr','water']
 monitors={k:monitor(p/('monitor_'+k+'.csv')) for k in keys}
 item={'id':j['id'],'inner_limit':j['inner'],'window':[lo,hi],'steps':len(h),'independent_history_finite':all(all(math.isfinite(v) for v in a.values()) for a in h),'residuals':{},'force_inner_changes':{}}
 for k in keys:
  m=monitors[k];end=[];ratio=[];last_half=[];full=[];missing=0;nonfinite=0
  for a in h:
   stop=int(a['iteration']);start=stop-j['inner']+1;middle=stop-j['inner']//2
   vals=[m.get(z) for z in [start,middle,stop]]
   if any(v is None for v in vals):missing+=1;continue
   if not all(math.isfinite(v) for v in vals):nonfinite+=1;continue
   first,mid,last=vals;end.append(last)
   if abs(first)>1e-300:ratio.append(abs(last/first))
   if abs(last)>1e-15:
    last_half.append(100*abs(last-mid)/abs(last));full.append(100*abs(last-first)/abs(last))
  if k in ['Fx_half_Monitor','Fz_half_Monitor']:
   field='Fx_slice_N' if k.startswith('Fx') else 'Fz_slice_N'
   match=max(abs(m[int(a['iteration'])]-a[field]) for a in h)
   item['force_inner_changes'][field]={'last_half_iterations_change_pct':stats(last_half),'first_to_last_change_pct':stats(full),'crosscheck_max_difference_N_vs_independent_report':match,'missing':missing,'nonfinite_in_window':nonfinite}
  else:item['residuals'][k]={'end_iteration':stats(end),'end_over_first_ratio':stats(ratio),'missing':missing,'nonfinite_in_window':nonfinite}
 sub=rows(p/'vof_substeps.csv');item['vof_substep_counts']=sorted(set(int(a['VOF_substeps']) for a in sub))
 fluid=rows(p/'fluid_fields.csv');alpha=[a['Volume Fraction of water'] for a in fluid];item['saved_phase_bounds']=[min(alpha),max(alpha)];item['saved_fields_all_finite']=all(all(math.isfinite(v) for v in a.values()) for a in fluid)
 item['phase_field_cells']=len(fluid)
 out['cases'].append(item)
state=read(R/'temporal_validation_state.json',{});active=state.get('active')
if active and (T/active/'history.csv').exists():
 h=rows(T/active/'history.csv');out['active_progress']={'id':active,'steps':len(h),'physical_time_s':h[-1]['physical_time_s'] if h else None,'all_recorded_values_finite':all(all(math.isfinite(v) for v in a.values()) for a in h)}
(R/'temporal_inner_convergence_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'cases':[{'id':a['id'],'force_inner_changes':a['force_inner_changes'],'phase_bounds':a['saved_phase_bounds'],'substep_counts':a['vof_substep_counts'],'finite':a['saved_fields_all_finite']} for a in out['cases']],'active':out.get('active_progress'),'conservation_status':out['conservation_status']},indent=2))
