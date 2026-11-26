"""Temporal tests against the preserved original M04 accepted mean."""
import json,html,datetime,hashlib,os
from pathlib import Path
R=Path(__file__).resolve().parent;T=R/'temporal_order_20261029'
def read(p,default=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return default
def f(v,n=3):return '—' if v is None else format(v,f'.{n}f')
def pct(v,base):return None if v is None or base is None or abs(base)<1e-15 else 100*(v-base)/abs(base)
def save(p,data):
 tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(p)
def comparison():
 plan=read(R/'temporal_validation_plan.json',{});bp=R/'M04_original_temporal_reference.json';base=read(bp)
 if not base:
  m=next((x for x in read(R/'mesh_convergence.json',{}).get('settled_results',[]) if x['id']=='M04'),None)
  if not m or not plan.get('jobs'):return None
  source=Path(plan['jobs'][0]['source']);history=source.parent/'history.csv'
  if source.parent.name!='M04_until_settled_r2' or abs(m['time_s']-plan['jobs'][0]['start'])>1e-8:raise ValueError('Original M04 source/window mismatch')
  base={'id':'M04 original','source_attempt':source.parent.name,'source_sim':str(source),'history_sha256':hashlib.sha256(history.read_bytes()).hexdigest(),'window':[m['window_start_s'],m['time_s']],'means':{'CD':m['CD'],'CL_total':m['CL_total'],'pressure_drag_N':m['Fx_pressure_N'],'viscous_drag_N':m['Fx_viscous_N']},'order':'FIRST_ORDER','dt_s':.001,'inner':20}
  save(bp,base)
 cases=[]
 for job in plan.get('jobs',[]):
  result=read(T/job['id']/'experiment_result.json',{})
  item={'id':job['id'],'short':job['id'].split('_')[0],'order':job['order'],'dt_s':job['dt'],'inner':job['inner'],'result':result}
  if result:
   item['means']={k:v['mean'] for k,v in result['last_window'].items()}
   item['difference_pct_vs_original']={k:pct(v,base['means'][k]) for k,v in item['means'].items()}
  cases.append(item)
 pairs=[]
 for ref,other,purpose in [('T01','T02','Time order'),('T02','T03','Time step'),('T02','T04','Inner iterations')]:
  a=next((c for c in cases if c['short']==ref),{});b=next((c for c in cases if c['short']==other),{})
  if a.get('means') and b.get('means'):
   pairs.append({'reference':ref,'comparison':other,'purpose':purpose,'difference_pct':{k:pct(v,a['means'][k]) for k,v in b['means'].items()},'both_windows_settled':a['result']['settling_check_pass'] and b['result']['settling_check_pass']})
 out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'baseline':base,'cases':cases,'matched_pairs':pairs,'formula':'100 * (test mean - original M04 mean) / abs(original M04 mean)','interpretation':'Original-versus-continuation comparison includes later physical-time drift. Same-window T02/T01 isolates time order. Adjacent-window settling below 0.5% is not a bound on accumulated drift or discretization error.'}
 save(R/'temporal_original_comparison.json',out);return out
def brief(data):
 if not data:return ''
 b=data['baseline'];s='<p class="temporal-baseline-note"><b>Original M04:</b> mean CD '+f(b['means']['CD'],6)+', mean CL '+f(b['means']['CL_total'],6)+' over '+f(b['window'][0])+'–'+f(b['window'][1])+' s.'
 t=next((c for c in data['cases'] if c['short']=='T01' and c.get('means')),None)
 if t:
  delta=t['difference_pct_vs_original'];s+=' Same-settings continuation T01: CD '+format(delta['CD'],'+.3f')+'%, CL '+format(delta['CL_total'],'+.3f')+'%.'
 return s+' <a href="#temporal-validation">Compare all test means with the original M04</a>.</p>'
def panel():
 d=comparison()
 if not d:return ''
 b=d['baseline'];state=read(R/'temporal_validation_state.json',{});active=(state.get('active') or '').split('_')[0]
 s='<div class="card" id="temporal-validation"><h3>Temporal tests · original M04 reference</h3><p>All tests continue the same saved M04 state at '+f(b['window'][1])+' s. T01 retains the original settings. T02 changes time order; T03 halves the step; T04 halves inner iterations. Spatial convection remains second order and VOF uses HRIC.</p>'
 s+='<p>Original M04 uses its accepted final 0.2 s mean. Completed tests use 2.042–2.242 s after a further 0.6 s of computation. These are different physical-time windows: differences from original M04 include continuing force drift.</p>'
 s+='<div class="table-wrap"><table class="temporal-reference-table"><thead><tr><th>Case / settings</th><th>Mean window [s]</th><th>Mean CD</th><th>CD vs original [%]</th><th>Mean CL</th><th>CL vs original [%]</th><th>Status</th></tr></thead><tbody>'
 s+='<tr class="original-reference-row"><th scope="row">M04 original<br><small>1st order · 1 ms · 20 inner</small></th><td>'+f(b['window'][0])+'–'+f(b['window'][1])+'</td><td>'+f(b['means']['CD'],6)+'</td><td>reference</td><td>'+f(b['means']['CL_total'],6)+'</td><td>reference</td><td>Accepted settling</td></tr>'
 for c in d['cases']:
  r=c['result'];v=c.get('means',{});delta=c.get('difference_pct_vs_original',{});settings=('2nd' if c['order']=='SECOND_ORDER' else '1st')+' order · '+f(c['dt_s']*1000,1)+' ms · '+str(c['inner'])+' inner'
  status=('Window settled' if r.get('settling_check_pass') else 'Extend matched tests') if r else ('Running' if c['short']==active and state.get('status')=='running' else 'Pending')
  window='–'.join(f(x) for x in r['comparison_window']) if r else 'Pending'
  s+='<tr data-temporal-case="'+c['short']+'"><th scope="row">'+c['short']+'<br><small>'+settings+'</small></th><td>'+window+'</td><td>'+f(v.get('CD'),6)+'</td><td>'+f(delta.get('CD'))+'</td><td>'+f(v.get('CL_total'),6)+'</td><td>'+f(delta.get('CL_total'))+'</td><td>'+status+'</td></tr>'
 s+='</tbody></table></div><p class="muted">Signed change = 100 × (test mean − original M04 mean) / |original M04 mean|. Pending tests have no final mean. The 0.5% settling check concerns adjacent 0.2 s windows; it does not limit cumulative drift or establish time accuracy.</p>'
 s+='<h4>Like-for-like comparisons · same physical-time window</h4>'
 if d['matched_pairs']:
  s+='<div class="table-wrap"><table><thead><tr><th>Comparison</th><th>Changed setting</th><th>CD change [%]</th><th>CL change [%]</th><th>Window checks</th></tr></thead><tbody>'
  for p in d['matched_pairs']:s+='<tr><td>'+p['comparison']+' vs '+p['reference']+'</td><td>'+p['purpose']+'</td><td>'+f(p['difference_pct']['CD'])+'</td><td>'+f(p['difference_pct']['CL_total'])+'</td><td>'+('Both pass' if p['both_windows_settled'] else 'Extend matched tests')+'</td></tr>'
  s+='</tbody></table></div>'
 else:s+='<p class="muted">Waiting for the second completed branch. T02/T01 isolates time order; T03/T02 tests the step; T04/T02 tests inner iterations.</p>'
 s+='<details><summary>Pressure / viscous drag and adjacent-window checks</summary><div class="table-wrap"><table><thead><tr><th>Case</th><th>Pressure Fx [N]</th><th>vs original [%]</th><th>Viscous Fx [N]</th><th>vs original [%]</th><th>Adjacent CD [%]</th><th>Adjacent CL [%]</th></tr></thead><tbody><tr><th>M04 original</th><td>'+f(b['means']['pressure_drag_N'],5)+'</td><td>reference</td><td>'+f(b['means']['viscous_drag_N'],5)+'</td><td>reference</td><td>—</td><td>—</td></tr>'
 for c in d['cases']:
  if not c.get('means'):continue
  v=c['means'];x=c['difference_pct_vs_original'];a=c['result']['adjacent_mean_change_pct']
  s+='<tr><th>'+c['short']+'</th><td>'+f(v['pressure_drag_N'],5)+'</td><td>'+f(x['pressure_drag_N'])+'</td><td>'+f(v['viscous_drag_N'],5)+'</td><td>'+f(x['viscous_drag_N'])+'</td><td>'+f(a['CD'])+'</td><td>'+f(a['CL_total'])+'</td></tr>'
 s+='</tbody></table></div></details><p class="muted">These tests remain separate from mesh selection. Final-mesh time-step and inner-convergence checks are still required.</p></div>'
 return '<style>#temporal-validation{scroll-margin-top:90px}.temporal-reference-table{min-width:920px}.temporal-reference-table th{text-transform:none;letter-spacing:0}.temporal-reference-table small{font-weight:400;white-space:nowrap}.original-reference-row{background:#edf4f8}.temporal-baseline-note{padding:12px;border-left:3px solid #0072b2;background:#f5f8fa}</style>'+s
