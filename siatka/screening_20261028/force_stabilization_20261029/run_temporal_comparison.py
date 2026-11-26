"""Exclusive GPU temporal-comparison queue; waits for accepted M08."""
import os,sys,time,json,csv,math,statistics,subprocess,ctypes
from pathlib import Path
import run_until_settled as e
from mesh_selection_queue import running
R=Path(__file__).resolve().parent;T=R/'temporal_order_20261029'
def state(status,**kw):e.write(R/'temporal_validation_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),**kw))
def refresh():
 q=e.read(T/'queue_state.json',{})
 state('running',active=q.get('active'),queue=q)
 e.write(R/'queue_state.json',{'status':'running','active':q.get('active','Temporal comparison'),'updated_at':e.stamp(),'purpose':'Separate M04 time-order test; mesh-selection means unchanged','waves_blocked_until_mesh_selected':True})
 try:subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
 except Exception:pass
def summarize(job,result):
 out=T/job['id']
 with (out/'history.csv').open() as f:rows=[{k:float(v) for k,v in a.items()} for a in csv.DictReader(f)]
 if not rows or not all(all(math.isfinite(v) for v in a.values()) for a in rows):raise RuntimeError('Non-finite independent history')
 end=job['target'];windows=[]
 for lo,hi in [(end-.4,end-.2),(end-.2,end)]:
  a=[x for x in rows if lo+1e-8<x['physical_time_s']<=hi+1e-8]
  if len(a)!=round(.2/job['dt']):raise RuntimeError('Incomplete comparison window')
  windows.append({k:{'mean':statistics.mean(x[k] for x in a),'rms':statistics.pstdev(x[k] for x in a)} for k in ['CD','CL_total','pressure_drag_N','viscous_drag_N']})
 changes={k:100*(windows[1][k]['mean']-windows[0][k]['mean'])/abs(windows[0][k]['mean']) for k in ['CD','CL_total']}
 timings=[b['wall_seconds']-a['wall_seconds'] for a,b in zip(rows,rows[1:]) if b['physical_time_s']>end-.2+1e-8]
 return {'id':job['id'],'dt_s':job['dt'],'order':job['order'],'start_s':job['start'],'end_s':rows[-1]['physical_time_s'],'comparison_window':[end-.2,end],'last_window':windows[1],'adjacent_mean_change_pct':changes,'settling_check_pass':all(abs(v)<.5 for v in changes.values()),'median_wall_s_per_step':statistics.median(timings),'source_unchanged':result['original_unchanged'],'last_interface_CFL':rows[-1]['interface_max_CFL']}
def main():
 own=T/'controller.lock';rootlock=R/'queue.lock';claimed=False
 if own.exists():raise RuntimeError('Temporal controller already registered; inspect before recovery')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'created_at':e.stamp()},f)
 try:
  while True:
   if (R/'STOP_ALL').exists() or (T/'STOP_ALL').exists():state('paused_by_marker');return
   result=e.read(R/'M08_until_settled_r3/controller_result.json',{})
   if result.get('status')=='completed' and not rootlock.exists():break
   state('waiting_for_M08',reason='Main M08 recovery/settling has GPU priority')
   time.sleep(30)
  with rootlock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M04 temporal comparison, separate from mesh selection'},f)
  claimed=True
  for j in e.read(R/'queue.json',[]):
   if not (R/j['id']/'controller_result.json').exists() and running(e.read(R/j['id']/'process.json',{}).get('launcher_pid')):raise RuntimeError('Existing campaign solver active')
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  plan=e.read(R/'temporal_validation_plan.json');e.ROOT=T;e.refresh=refresh;results=[]
  for j in plan['jobs']:
   if (R/'STOP_ALL').exists() or (T/'STOP_ALL').exists():state('paused_by_marker',results=results);return
   if (T/j['id']).exists():raise RuntimeError('Attempt exists; recover with a new ID')
   state('starting',active=j['id'],results=results)
   result=e.run_job(j);done=result.get('completed',{})
   if result['returncode']!=0 or done.get('status')!='target_reached' or abs(done.get('time_s',-1)-j['target'])>j['dt']*.1 or not result['original_unchanged']:raise RuntimeError('Experiment failed guard: '+j['id'])
   item=summarize(j,result);results.append(item)
   e.write(T/j['id']/'experiment_result.json',dict(status='completed_fixed_horizon',**item))
   pairs=[]
   for a,b in [(0,1),(1,2)]:
    if len(results)>b:pairs.append({'reference':results[a]['id'],'comparison':results[b]['id'],'difference_pct_vs_reference':{k:100*(results[b]['last_window'][k]['mean']-results[a]['last_window'][k]['mean'])/abs(results[a]['last_window'][k]['mean']) for k in ['CD','CL_total','pressure_drag_N','viscous_drag_N']}})
   e.write(R/'temporal_validation_results.json',{'updated_at':e.stamp(),'cases':results,'pairs':pairs,'all_windows_settled':all(x['settling_check_pass'] for x in results),'interpretation':'Screen only; investigate/extend if drift fails0.5%; no automatic mesh or temporal acceptance.'})
  state('completed_screen',results=results)
  e.write(R/'queue_state.json',{'status':'awaiting_mesh_selection','updated_at':e.stamp(),'temporal_screen':'complete; results require review','waves_blocked_until_mesh_selected':True})
 except BaseException as ex:
  state('needs_review',error=str(ex))
  if claimed:e.write(R/'queue_state.json',{'status':'needs_review','updated_at':e.stamp(),'error':'Temporal comparison: '+str(ex),'waves_blocked_until_mesh_selected':True})
  raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if claimed and e.read(rootlock,{}).get('pid')==os.getpid():rootlock.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
  subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
if __name__=='__main__':main()
