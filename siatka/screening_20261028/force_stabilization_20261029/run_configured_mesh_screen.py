"""Separate matched-setting calm mesh screen. Default prepares only; --run launches after evidence gates."""
import argparse,csv,ctypes,json,math,os,statistics,subprocess,sys
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';P=R/'configured_mesh_20261029'
CONFIG={'order':'SECOND_ORDER','dt_s':.001,'inner_iterations':10,'scope':'Calm mesh screening; selected-mesh time-step and wave propagation checks remain required'}
def write(p,obj):e.write(p,obj)
def read(p,d=None):return e.read(p,d)
def rows(p):
 with p.open(encoding='utf-8-sig') as f:return [{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
def state(status,**kw):write(R/'configured_mesh_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),**kw))
def refresh():
 q=read(P/'queue_state.json',{});active=q.get('active')
 if active:
  state('running',active=active,queue=q,configuration=CONFIG)
  write(R/'queue_state.json',dict(status='running',active=active,purpose='Matched second-order calm mesh screen',updated_at=e.stamp(),waves_blocked_until_mesh_selected=True))
  if (R/'STOP_ALL').exists():(P/active/'STOP').touch()
 try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
 except Exception:pass
def prepare():
 P.mkdir(exist_ok=True)
 macro=(R/'conservation_probe_20261029/ContinueUntilSettled.java').read_text()
 anchor='if(false){ // Fixed matched horizon for temporal-order experiment'
 if macro.count(anchor)!=1:raise RuntimeError('Unexpected diagnostic macro; preserve existing files')
 macro=macro.replace(anchor,'if(steps%10==0&&t>=Math.max(1.0,startTime+.4)-dt*.1){ // First pass after two new-setting windows')
 macro=macro.replace('Initialization allowed only for new M04 at t=0','Initialization allowed only for new audited mesh at t=0')
 target=P/'ContinueUntilSettled.java'
 if target.exists() and target.read_text()!=macro:raise RuntimeError('Prepared macro differs; inspect before replacing')
 if not target.exists():target.write_text(macro,encoding='utf-8')
 warm={'id':'M09_startup_dt05ms_inner50_r1','mesh':'M09','source':str(Q/'M09/mesh.sim'),'start':0.,'cells':214908,'initialize':True,'dt':.0005,'inner':50,'order':'FIRST_ORDER','target':.020,'wall_budget_s':1800,'purpose':'Guarded startup checkpoint only; excluded from mesh comparison'}
 jobs=[warm]
 for mesh,source,start,cells in [('M09',P/warm['id']/'final.sim',.020,214908),('M08',R/'M08_until_settled_r3/final.sim',1.600,254989),('M07',R/'M07_until_settled_r1/final.sim',1.640,481635)]:
  jobs.append({'id':mesh+'_SO1ms_inner10_r1','mesh':mesh,'source':str(source),'start':start,'cells':cells,'initialize':False,'dt':.001,'inner':10,'order':'SECOND_ORDER','target':10.,'wall_budget_s':14400,'prior_history':'','purpose':'First passing adjacent 0.2s means below0.5%, using only new-setting history and at least0.4s continuation'})
 plan={'created_at':e.stamp(),'namespace':str(P),'configuration':CONFIG,'jobs':jobs,'preserve_historical_results':True,'macro_sha256':e.digest(target),'max_mesh_id':'M15','launch':str(R/'run_configured_mesh_screen.py')+' --run','waves_admitted':False}
 old=read(P/'plan.json')
 if old:
  if old['jobs']!=jobs or old['macro_sha256']!=plan['macro_sha256']:raise RuntimeError('Existing plan differs; preserve attempt')
  plan=old
 else:write(P/'plan.json',plan)
 if not (R/'configured_mesh_plan.json').exists():write(R/'configured_mesh_plan.json',plan)
 if not (R/'configured_mesh_state.json').exists():state('prepared_not_launched',configuration=CONFIG,jobs=[j['id'] for j in jobs])
 return plan
def evidence_gate():
 t=read(R/'temporal_validation_results.json',{});cases={x['id'].split('_')[0]:x for x in t.get('cases',[])}
 if set(cases)!=set(['T01','T02','T03','T04']) or not all(x.get('settling_check_pass') and x.get('source_unchanged') for x in cases.values()):raise RuntimeError('Temporal evidence incomplete')
 pairs={b:{k:100*(cases[b]['last_window'][k]['mean']/cases['T02']['last_window'][k]['mean']-1) for k in ['CD','CL_total']} for b in ['T03','T04']}
 if any(abs(v)>.25 for pair in pairs.values() for v in pair.values()):raise RuntimeError('Configuration sensitivity requires review')
 probe=read(R/'conservation_probe_results.json',{});pr={x['id']:x for x in probe.get('results',[])}
 expected={'Cmass_SO1ms_inner20_r1','Cmass_SO1ms_inner10_r1'}
 if set(pr)!=expected or read(R/'conservation_probe_state.json',{}).get('status')!='completed_pending_review':raise RuntimeError('Conservation probes not completed')
 for ident,x in pr.items():
  done=read(R/'conservation_probe_20261029'/ident/'controller_result.json',{})
  if x.get('steps')!=40 or not done.get('original_unchanged') or done.get('returncode')!=0:raise RuntimeError('Probe identity/preservation failure')
  for scheme in ['backward_euler_budget_pct_of_inlet','BDF2_budget_pct_of_inlet']:
   v=x[scheme]['max_abs_pct']
   if not math.isfinite(v) or v>.01:raise RuntimeError('Mass-budget diagnostic above0.01% inlet; review before new mesh flow')
 audit=read(R/'professor_inner_audit.json',{});fields={x['id']:x for x in audit.get('cases',[])}
 for ident in ['T02_M04_SO_dt1ms_r1','T04_M04_SO_dt1ms_inner10_r1']:
  x=fields.get(ident,{})
  if not x.get('fields_all_finite') or not x.get('all_history_finite') or x.get('steps')!=200 or x.get('phase_bounds')!=[0.,1.]:raise RuntimeError('Final field/inner audit incomplete')
  for name in ['Fx_half_Monitor','Fz_half_Monitor']:
   m=x['monitors'][name]
   if m['missing'] or m['nonfinite'] or m['independent_crosscheck_max_N']>1e-8 or m['half_iterations_change_pct']['max']>.01:raise RuntimeError('Inner force diagnostic requires review')
 decision={'updated_at':e.stamp(),'status':'supported_for_calm_mesh_screen','configuration':CONFIG,'same_window_pct_vs_T02':pairs,'conservation_probes':list(pr.values()),'evidence':['temporal_validation_results.json','temporal_original_comparison.json','professor_inner_audit.json','conservation_probe_results.json'],'limits':['M04 calm screen only; final selected mesh requires own temporal check','Mass residual includes accumulation; not merely outlet-minus-inlet','VOF API reports one substep; no claim of effective dynamic multistepping','No wave propagation accuracy claim']}
 return decision
def verify_mesh():
 build=read(R/'M09_build_result.json',{})
 m=read(Q/'M09/measurement.json',{}).get('metrics',{});top=read(Q/'M09/topology_audit.json',{})
 if build.get('status')!='verified_ready_pending_temporal_review' or build.get('cells')!=214908 or m.get('cell_count')!=214908:raise RuntimeError('M09 audited identity mismatch')
 if any(m.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError('M09 topology/geometry gate failed')
 if m.get('min_cell_quality',0)<.01 or m.get('min_face_validity',0)<.5:raise RuntimeError('M09 quality requires review')
 for mesh,ident in [('M08','M08_until_settled_r3'),('M07','M07_until_settled_r1')]:
  r=read(R/ident/'controller_result.json',{})
  if r.get('status')!='completed' or not r.get('original_unchanged'):raise RuntimeError('Historical accepted source not preserved: '+mesh)
def summarize(j,r):
 p=P/j['id'];h=rows(p/'history.csv')
 if not h or not all(math.isfinite(v) for x in h for v in x.values()):raise RuntimeError('Nonfinite independent history')
 if any(abs(x['dt_s']-j['dt'])>1e-10 for x in h):raise RuntimeError('Unexpected time step')
 n=round(.2/j['dt'])
 if len(h)<2*n:raise RuntimeError('Fewer than two new-setting windows')
 a,b=h[-2*n:-n],h[-n:]
 means=lambda w:{k:statistics.mean(x[k] for x in w) for k in ['CD','CL_total','pressure_drag_N','viscous_drag_N']}
 prev,mean=means(a),means(b);changes={k:100*(mean[k]-prev[k])/abs(prev[k]) for k in ['CD','CL_total']}
 if any(abs(v)>=.5 for v in changes.values()):raise RuntimeError('Independent settling cross-check failed')
 field=rows(p/'fluid_fields.csv');phase=[x['Volume Fraction of water'] for x in field]
 if not all(math.isfinite(v) for x in field for v in x.values()) or min(phase)<-1e-8 or max(phase)>1+1e-8:raise RuntimeError('Saved field bounds/finite gate failed')
 timing=[y['wall_seconds']-x['wall_seconds'] for x,y in zip(h[-n-1:],h[-n:])]
 return {'id':j['id'],'mesh':j['mesh'],'cells':j['cells'],'order':j['order'],'dt_s':j['dt'],'inner_iterations':j['inner'],'status':'force_settled_configuration_matched','source_unchanged':r['original_unchanged'],'window':[h[-1]['physical_time_s']-.2,h[-1]['physical_time_s']],'means':mean,'adjacent_mean_change_pct':changes,'median_wall_s_per_step':statistics.median(timing),'last_interface_CFL':h[-1]['interface_max_CFL'],'phase_bounds':[min(phase),max(phase)],'all_saved_fields_finite':True,'source_sim':str(p/'final.sim')}
def comparison(results):
 pairs=[]
 for i,a in enumerate(results):
  for b in results[i+1:]:
   delta={k:100*(a['means'][k]-b['means'][k])/abs(b['means'][k]) for k in a['means']}
   pairs.append({'candidate':a['mesh'],'reference':b['mesh'],'formula':'100*(candidate-reference)/abs(reference)','difference_pct':delta,'both_force_coefficients_within_1pct':all(abs(delta[k])<=1 for k in ['CD','CL_total'])})
 return {'updated_at':e.stamp(),'configuration':CONFIG,'results':results,'pairs':pairs,'interpretation':'Matched solver settings, each first settled final0.2s window; no automatic final mesh selection. Check component-wise refinement, remaining drift, wall fields and selected-mesh dt.'}
def main(run=False):
 plan=prepare()
 if not run:print(json.dumps({'status':'prepared_not_launched','jobs':[j['id'] for j in plan['jobs']]}));return
 decision=evidence_gate();verify_mesh();lock=R/'queue.lock';own=P/'controller.lock';claimed=False
 if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():raise RuntimeError('Campaign pause marker present')
 if lock.exists() or own.exists():raise RuntimeError('Existing controller lock; inspect before launch')
 for folder in [R,R/'temporal_order_20261029',R/'conservation_probe_20261029',P]:
  for proc in folder.glob('*/process.json'):
   if not (proc.parent/'controller_result.json').exists() and running(read(proc,{}).get('launcher_pid')):raise RuntimeError('Existing owned campaign solver remains active')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'created_at':e.stamp()},f)
 results=[]
 try:
  with lock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M09 guarded startup and matched M09/M08/M07 SO1ms10-inner'},f)
  claimed=True;ctypes.windll.kernel32.SetThreadExecutionState(0x80000001);e.ROOT=P;e.refresh=refresh
  write(R/'calm_solver_configuration_decision.json',decision)
  for index,j in enumerate(plan['jobs']):
   if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():state('paused_by_marker',results=results);return
   if (P/j['id']).exists():raise RuntimeError('Attempt exists; preserve it and recover with a new ID')
   state('starting',active=j['id'],configuration=CONFIG,results=results)
   r=e.run_job(j);done=r.get('completed',{})
   if r.get('returncode')!=0 or not r.get('original_unchanged'):raise RuntimeError('Execution/source-preservation failure: '+j['id'])
   if index==0:
    h=rows(P/j['id']/'history.csv')
    if done.get('status')!='target_reached' or abs(done.get('time_s',-1)-.020)>1e-8 or len(h)!=40 or not all(math.isfinite(v) for x in h for v in x.values()) or h[-1]['max_velocity_m_s']>50:raise RuntimeError('M09 guarded startup failed; preserve and recover a new attempt')
    write(P/j['id']/'startup_acceptance.json',{'status':'startup_checkpoint_only','time_s':done['time_s'],'last_max_velocity_m_s':h[-1]['max_velocity_m_s'],'not_force_accepted':True})
   else:
    if r.get('status')!='completed' or done.get('status')!='stabilized':raise RuntimeError('Force settling not accepted: '+j['id'])
    item=summarize(j,r);results.append(item);write(P/j['id']/'configured_result.json',item);write(R/'configured_mesh_results.json',comparison(results))
   refresh()
  state('completed_pending_mesh_review',configuration=CONFIG,results=results)
  write(R/'queue_state.json',dict(status='matched_mesh_review',updated_at=e.stamp(),purpose='Matched M09/M08/M07 complete; field/time review required',waves_blocked_until_mesh_selected=True))
 except BaseException as ex:
  state('needs_review',error=str(ex),results=results)
  if claimed:write(R/'queue_state.json',dict(status='needs_review',updated_at=e.stamp(),error='Configured mesh screen: '+str(ex),waves_blocked_until_mesh_selected=True))
  raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if claimed and read(lock,{}).get('pid')==os.getpid():lock.unlink()
  if read(own,{}).get('pid')==os.getpid():own.unlink()
  try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
  except Exception:pass
if __name__=='__main__':
 args=argparse.ArgumentParser();args.add_argument('--run',action='store_true');main(args.parse_args().run)
