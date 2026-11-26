"""Match already-settled SO mesh histories at one physical endpoint; preserve every source."""
import os,time,json,csv,math,statistics,subprocess,ctypes
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent;P=R/'matched_endpoint_20261029';C=R/'configured_mesh_20261029'
KEYS=['CD','CL_total','pressure_drag_N','viscous_drag_N']
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
def state(status,**kw):e.write(R/'matched_endpoint_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),**kw))
def refresh():
 q=e.read(P/'queue_state.json',{});state('running',active=q.get('active'),queue=q,plan=e.read(R/'matched_endpoint_plan.json',{}))
 e.write(R/'queue_state.json',dict(status='running',active=q.get('active'),purpose='Matched physical endpoint for settled SO mesh comparison',updated_at=e.stamp(),waves_blocked_until_mesh_selected=True))
 if (R/'STOP_ALL').exists() and q.get('active'):(P/q['active']/'STOP').touch()
 try:subprocess.run([os.sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 except Exception:pass
def summarize(source,job=None,result=None):
 sp=Path(source['source_sim']).parent;h=rows(sp/'history.csv');end=target
 paths=[str(sp/'history.csv')];out=sp
 if job:
  out=P/job['id'];h+=rows(out/'history.csv');paths.append(str(out/'history.csv'))
 if not all(math.isfinite(v) for x in h for v in x.values()):raise RuntimeError('Nonfinite independent history')
 selected=[x for x in h if end-.4+1e-8<x['physical_time_s']<=end+1e-8]
 if len(selected)!=400 or any(abs(b['physical_time_s']-a['physical_time_s']-.001)>1e-8 for a,b in zip(selected,selected[1:])):raise RuntimeError('Missing/overlapping same-setting comparison samples')
 a,b=selected[:200],selected[200:];prev={k:statistics.mean(x[k] for x in a) for k in KEYS};means={k:statistics.mean(x[k] for x in b) for k in KEYS}
 changes={k:100*(means[k]-prev[k])/abs(prev[k]) for k in ['CD','CL_total']}
 fluid=rows(out/'fluid_fields.csv');alpha=[x['Volume Fraction of water'] for x in fluid]
 finite=all(math.isfinite(v) for x in fluid for v in x.values())
 if not finite or min(alpha)<-1e-8 or max(alpha)>1+1e-8:raise RuntimeError('Saved field audit failed')
 combined=out/'matched_history.csv' if job else None
 if combined:
  with combined.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(h[0]));w.writeheader();w.writerows(h)
 return {'mesh':source['mesh'],'id':job['id'] if job else source['id'],'cells':source['cells'],'order':'SECOND_ORDER','dt_s':.001,'inner_iterations':10,'status':'matched_endpoint_review','window':[end-.2,end],'means':means,'adjacent_mean_change_pct':changes,'settling_check_pass':all(abs(v)<.5 for v in changes.values()),'source_unchanged':result['original_unchanged'] if result else source['source_unchanged'],'all_saved_fields_finite':finite,'phase_bounds':[min(alpha),max(alpha)],'last_interface_CFL':b[-1]['interface_max_CFL'],'source_sim':str(out/'final.sim'),'history_sources':paths,'combined_history':str(combined) if combined else str(sp/'history.csv'),'reused_accepted_field':job is None,'force_component_sum_max_error_N':max(abs(x['Fx_slice_N']-x['pressure_drag_N']-x['viscous_drag_N']) for x in selected)}
def save_results(results):
 pairs=[]
 for a in results:
  for b in results:
   if a['cells']>=b['cells']:continue
   d={k:100*(a['means'][k]-b['means'][k])/abs(b['means'][k]) for k in KEYS}
   pairs.append({'candidate':a['mesh'],'reference':b['mesh'],'difference_pct':d,'both_force_coefficients_within_1pct':all(abs(d[k])<=1 for k in ['CD','CL_total'])})
 e.write(R/'matched_endpoint_results.json',dict(updated_at=e.stamp(),target_s=target,window=[target-.2,target],results=results,pairs=pairs,interpretation='Same SO1ms10 settings and same physical windows; source histories joined only across continuous identical-setting checkpoints. Geometry/inner/conservation and selected-mesh timestep reviews remain; no automatic wave admission.'))
def main():
 global target
 P.mkdir(exist_ok=True);own=P/'controller.lock';root=R/'queue.lock';claimed=False
 if own.exists():raise RuntimeError('Existing matched-endpoint controller; inspect')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'Wait for configured meshes then align endpoint'},f)
 results=[]
 try:
  while True:
   if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():state('paused_by_marker');return
   st=e.read(R/'configured_mesh_state.json',{})
   if st.get('status')=='needs_review':raise RuntimeError('Prior configured cohort requires recovery, not automatic continuation')
   if st.get('status')=='completed_pending_mesh_review' and not root.exists() and not running(st.get('controller_pid')):break
   state('waiting_for_M07',reason='Existing configured-mesh controller retains GPU priority');time.sleep(15)
  sources=e.read(R/'configured_mesh_results.json',{}).get('results',[])
  if {x['mesh'] for x in sources}!={'M09','M08','M07'}:raise RuntimeError('Incomplete configured cohort')
  for x in sources:
   if x['status']!='force_settled_configuration_matched' or not x['source_unchanged'] or not x['all_saved_fields_finite'] or x['order']!='SECOND_ORDER' or x['dt_s']!=.001 or x['inner_iterations']!=10:raise RuntimeError('Source acceptance/settings gate failed')
   pr=e.read(Path(x['source_sim']).parent/'process.json',{})
   if running(pr.get('launcher_pid')):raise RuntimeError('Prior owned GPU solver still active')
  target=round(max(x['window'][1] for x in sources),3)
  if target>3 or target<2:raise RuntimeError('Unexpected endpoint; review before continuation')
  macro=(R/'conservation_probe_20261029/ContinueUntilSettled.java').read_text()
  if 'if(false){ // Fixed matched horizon for temporal-order experiment' not in macro:raise RuntimeError('Unexpected fixed-horizon macro')
  mp=P/'ContinueUntilSettled.java'
  if mp.exists():raise RuntimeError('Prepared namespace exists; preserve and recover new ID')
  mp.write_text(macro)
  jobs=[]
  for x in sources:
   start=round(x['window'][1],3)
   if target-start<.0005:
    results.append(summarize(x));continue
   if target-start>1:raise RuntimeError('Unexpected extension length')
   jobs.append({'id':x['mesh']+'_SO_common_t'+str(round(target*1000))+'_r1','mesh':x['mesh'],'source':x['source_sim'],'start':start,'cells':x['cells'],'initialize':False,'dt':.001,'inner':10,'order':'SECOND_ORDER','target':target,'wall_budget_s':3600,'prior_history':str(Path(x['source_sim']).parent/'history.csv'),'purpose':'Fixed matched endpoint diagnostic after accepted first settling; unchanged solver settings, no new mesh'})
  plan={'updated_at':e.stamp(),'target_s':target,'comparison_window':[target-.2,target],'source_cohort':'configured_mesh_20261029','sources':sources,'jobs':jobs,'reused':[x['mesh'] for x in results],'waves_admitted':False,'macro_sha256':e.digest(mp)}
  e.write(R/'matched_endpoint_plan.json',plan);e.write(P/'plan.json',plan)
  with root.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'Align M09/M08 to accepted M07 physical endpoint for mesh comparison'},f)
  claimed=True;ctypes.windll.kernel32.SetThreadExecutionState(0x80000001);e.ROOT=P;e.refresh=refresh;save_results(results)
  for j in jobs:
   if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():state('paused_by_marker',results=results);return
   if (P/j['id']).exists():raise RuntimeError('Attempt exists; preserve')
   state('starting',active=j['id'],target_s=target)
   r=e.run_job(j);done=r.get('completed',{})
   if r['returncode']!=0 or not r['original_unchanged'] or done.get('status')!='target_reached' or abs(done.get('time_s',-1)-target)>1e-8:raise RuntimeError('Matched endpoint execution failed')
   src=next(x for x in sources if x['mesh']==j['mesh']);item=summarize(src,j,r);e.write(P/j['id']/'matched_result.json',item);results.append(item);save_results(results);refresh()
  state('completed_pending_selection_review',target_s=target,results=results)
  e.write(R/'queue_state.json',dict(status='matched_endpoint_review',updated_at=e.stamp(),purpose='Matched endpoint results ready; select only after diagnostics and timestep review',waves_blocked_until_mesh_selected=True))
 except BaseException as ex:state('needs_review',error=str(ex),results=results);raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if claimed and e.read(root,{}).get('pid')==os.getpid():root.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
  try:subprocess.run([os.sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
  except Exception:pass
if __name__=='__main__':main()
