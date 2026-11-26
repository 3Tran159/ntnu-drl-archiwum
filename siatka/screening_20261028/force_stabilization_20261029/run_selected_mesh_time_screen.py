"""Conditional selected-mesh dt screen. Reuses the matched 1ms branch; no duplicate baseline."""
import os,time,csv,math,statistics,json,subprocess,ctypes
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent;T=R/'selected_mesh_time_20261029'
def state(status,**kw):e.write(R/'selected_mesh_time_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),**kw))
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
def refresh():
 q=e.read(T/'queue_state.json',{});state('running',active=q.get('active'),queue=q,plan=e.read(R/'selected_mesh_time_plan.json',{}))
 e.write(R/'queue_state.json',dict(status='running',active=q.get('active'),purpose='Selected M09 timestep sensitivity: SO0.5ms versus reused SO1ms at common endpoint',updated_at=e.stamp(),waves_blocked_until_mesh_selected=True))
 if (R/'STOP_ALL').exists() and q.get('active'):(T/q['active']/'STOP').touch()
 try:subprocess.run([os.sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 except Exception:pass
def monitor(p):
 with p.open() as f:
  a=csv.reader(f);next(a);return {int(float(x[0])):float(x[1]) for x in a}
def main():
 T.mkdir(exist_ok=True);own=T/'controller.lock';root=R/'queue.lock';claimed=False
 if own.exists():raise RuntimeError('Existing selected-mesh time controller')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'Wait for matched M09 mesh support, then single dt half-step branch'},f)
 try:
  while True:
   if (R/'STOP_ALL').exists() or (T/'STOP_ALL').exists():state('paused_by_marker');return
   st=e.read(R/'matched_endpoint_state.json',{})
   if st.get('status')=='needs_review':raise RuntimeError('Matched endpoint cohort needs review')
   if st.get('status')=='completed_pending_selection_review' and not root.exists() and not running(st.get('controller_pid')):break
   state('waiting_for_matched_meshes',reason='M09 must agree with both finer M08/M07 before selected-mesh dt screen');time.sleep(15)
  data=e.read(R/'matched_endpoint_results.json',{});rr={x['mesh']:x for x in data.get('results',[])}
  if set(rr)!={'M09','M08','M07'}:raise RuntimeError('Incomplete matched cohort')
  for x in rr.values():
   if not x['source_unchanged'] or not x['all_saved_fields_finite'] or not x['settling_check_pass']:raise RuntimeError('Matched source diagnostics failed')
  pairs=[x for x in data['pairs'] if x['candidate']=='M09']
  if {x['reference'] for x in pairs}!={'M08','M07'} or not all(x['both_force_coefficients_within_1pct'] for x in pairs):
   state('mesh_gate_not_met',reason='Do not select M09 or launch dt branch: both finer confirmations must pass1%',pairs=pairs);return
  yp={x['mesh']:x for x in e.read(R/'configured_wall_yplus_audit.json',{}).get('cases',[])}
  if yp.get('M09',{}).get('area_weighted_yplus_p95',99)>1 or yp['M09']['wall_area_yplus_below_1_pct']<99:raise RuntimeError('M09 wall distribution review required')
  plan=e.read(R/'matched_endpoint_plan.json',{});src=next(x for x in plan['sources'] if x['mesh']=='M09');end=data['target_s'];start=src['window'][1]
  if end-start<.4-1e-8 or end-start>1:raise RuntimeError('Insufficient or unexpected dt comparison horizon')
  source=Path(src['source_sim']);identity=e.read(source.parent/'source_identity.json',{})
  reference=rr['M09']
  j={'id':'M09_SO_dt05ms_common_t'+str(round(end*1000))+'_r1','mesh':'M09','source':str(source),'start':start,'cells':src['cells'],'initialize':False,'dt':.0005,'inner':10,'order':'SECOND_ORDER','target':end,'wall_budget_s':5400,'prior_history':'','purpose':'One half-step branch from the identical checkpoint as matched1ms reference; no mixed-dt history'}
  macro=(R/'conservation_probe_20261029/ContinueUntilSettled.java').read_text()
  if 'if(false){ // Fixed matched horizon for temporal-order experiment' not in macro or (T/'ContinueUntilSettled.java').exists():raise RuntimeError('Unexpected or preexisting namespace')
  (T/'ContinueUntilSettled.java').write_text(macro)
  p={'updated_at':e.stamp(),'job':j,'reference':reference,'mesh_pairs':pairs,'diagnostic_threshold_pct':.25,'comparison_window':[end-.2,end],'interpretation':'Two-step sensitivity check, not formal temporal order/GCI; calm mesh only, separate wave accuracy gate'}
  e.write(R/'selected_mesh_time_plan.json',p);e.write(T/'plan.json',p)
  if running(e.read(source.parent/'process.json',{}).get('launcher_pid')):raise RuntimeError('Owned source solver still active')
  with root.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M09 selected-mesh half timestep check after matched mesh agreement'},f)
  claimed=True;ctypes.windll.kernel32.SetThreadExecutionState(0x80000001);e.ROOT=T;e.refresh=refresh;state('starting',active=j['id'],plan=p)
  run=e.run_job(j);done=run.get('completed',{});out=T/j['id']
  if run['returncode']!=0 or not run['original_unchanged'] or done.get('status')!='target_reached' or abs(done.get('time_s',-1)-end)>1e-8:raise RuntimeError('Selected dt execution failed')
  h=rows(out/'history.csv')
  if not h or not all(math.isfinite(v) for x in h for v in x.values()):raise RuntimeError('Nonfinite dt history')
  windows=[[x for x in h if lo+1e-8<x['physical_time_s']<=hi+1e-8] for lo,hi in [(end-.4,end-.2),(end-.2,end)]]
  if any(len(w)!=400 for w in windows):raise RuntimeError('Incomplete same-window dt sample')
  keys=['CD','CL_total','pressure_drag_N','viscous_drag_N'];means=[{k:statistics.mean(x[k] for x in w) for k in keys} for w in windows]
  delta={k:100*(means[1][k]-reference['means'][k])/abs(reference['means'][k]) for k in keys}
  drift={k:100*(means[1][k]-means[0][k])/abs(means[0][k]) for k in ['CD','CL_total']}
  fluid=rows(out/'fluid_fields.csv');alpha=[x['Volume Fraction of water'] for x in fluid];finite=all(math.isfinite(v) for x in fluid for v in x.values())
  if not finite or min(alpha)<-1e-8 or max(alpha)>1+1e-8:raise RuntimeError('Final saved field audit failed')
  inner={}
  for name,key in [('Fx_half_Monitor','Fx_slice_N'),('Fz_half_Monitor','Fz_slice_N')]:
   m=monitor(out/('monitor_'+name+'.csv'));changes=[];cross=[]
   for x in windows[1]:
    it=int(x['iteration']);a,b=m[it-5],m[it]
    if not math.isfinite(a) or not math.isfinite(b):raise RuntimeError('Nonfinite final inner force')
    changes.append(100*abs(b-a)/abs(b));cross.append(abs(b-x[key]))
   inner[name]={'max_half_iteration_change_pct':max(changes),'max_independent_difference_N':max(cross)}
  budget=rows(out/'conservation.csv');res=[]
  for i in range(2,len(budget)):
   x=budget[i]
   if x['time_s']<=end-.2+1e-8:continue
   val=(3*x['mass_kg']-4*budget[i-1]['mass_kg']+budget[i-2]['mass_kg'])/(2*.0005)+x['net_outward_mass_kg_s']
   if x['inward_mass_kg_s']<=0 or not math.isfinite(val):raise RuntimeError('Invalid mass budget')
   res.append(100*abs(val)/x['inward_mass_kg_s'])
  passed=all(abs(delta[k])<.25 and abs(drift[k])<.5 for k in ['CD','CL_total']) and max(res)<.01 and all(x['max_half_iteration_change_pct']<.01 and x['max_independent_difference_N']<1e-8 for x in inner.values())
  result={'updated_at':e.stamp(),'id':j['id'],'mesh':'M09','status':'time_step_screen_pass' if passed else 'needs_review','same_start_s':start,'window':[end-.2,end],'reference':reference,'half_step_means':means[1],'half_vs_1ms_difference_pct':delta,'adjacent_mean_change_pct':drift,'inner_forces':inner,'max_BDF2_mass_budget_pct_of_inlet':max(res),'phase_bounds':[min(alpha),max(alpha)],'all_saved_fields_finite':finite,'source_unchanged':run['original_unchanged'],'source_sim':str(out/'final.sim'),'scope':'Calm selected mesh sensitivity only; not wave propagation acceptance'}
  e.write(R/'selected_mesh_time_results.json',result);e.write(out/'experiment_result.json',result)
  if passed:
   decision={'updated_at':e.stamp(),'status':'supported_calm_mesh_template','mesh':'M09','cells':src['cells'],'configuration':{'time_order':'SECOND_ORDER','dt_s':.001,'inner':10},'common_mesh_window':[end-.2,end],'finer_confirmations':pairs,'dt_sensitivity':result,'wall_diagnostic':yp['M09'],'limitations':['Practical component-wise refinement, not formal GCI','TE has localized high-y+ outlier','Pressure and viscous components remain separately reported','Longer wave-domain/free-surface mesh and wave dt/propagation/domain checks remain required'],'waves_admitted':False}
   e.write(R/'selected_mesh_decision.json',decision)
  state('completed_supported' if passed else 'needs_review',result=result)
  e.write(R/'queue_state.json',dict(status='calm_mesh_supported_wave_checks_pending' if passed else 'needs_review',updated_at=e.stamp(),purpose='Selected-mesh timestep screen finished; inspect results',waves_blocked_until_wave_checks=True))
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if claimed and e.read(root,{}).get('pid')==os.getpid():root.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
  try:subprocess.run([os.sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
  except Exception:pass
if __name__=='__main__':main()
