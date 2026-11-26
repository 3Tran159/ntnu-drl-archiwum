"""Bounded matched GPU mass-budget probes, only after the existing temporal queue."""
import os,json,time,sys,csv,math,statistics,subprocess,ctypes
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent;P=R/'conservation_probe_20261029'
def state(status,**kw):e.write(R/'conservation_probe_state.json',dict(status=status,controller_pid=os.getpid(),updated_at=e.stamp(),**kw))
def refresh():
 q=e.read(P/'queue_state.json',{});state('running',active=q.get('active'),queue=q)
 e.write(R/'queue_state.json',dict(status='running',active=q.get('active'),purpose='Matched mass conservation diagnostics',updated_at=e.stamp()))
 subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
def summary(j):
 p=P/j['id']
 with (p/'conservation.csv').open() as f:a=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 if len(a)!=41 or not all(all(math.isfinite(v) for v in r.values()) for r in a):raise RuntimeError('Incomplete/nonfinite conservation record')
 dt=j['dt'];be=[];bdf2=[];integrated=0
 for i in range(1,len(a)):
  x,y=a[i-1],a[i]
  if abs(y['time_s']-x['time_s']-dt)>1e-9:raise RuntimeError('Time increment mismatch')
  integrated+=dt*(x['net_outward_mass_kg_s']+y['net_outward_mass_kg_s'])/2
  be.append(100*((y['mass_kg']-x['mass_kg'])/dt+y['net_outward_mass_kg_s'])/y['inward_mass_kg_s'])
  if i>=2:bdf2.append(100*((3*y['mass_kg']-4*x['mass_kg']+a[i-2]['mass_kg'])/(2*dt)+y['net_outward_mass_kg_s'])/y['inward_mass_kg_s'])
 stats=lambda v:{'median_signed_pct':statistics.median(v),'max_abs_pct':max(map(abs,v))}
 return {'id':j['id'],'steps':40,'start_s':a[0]['time_s'],'end_s':a[-1]['time_s'],'mass_change_kg':a[-1]['mass_kg']-a[0]['mass_kg'],'net_outward_flux_integral_trapezoid_kg':integrated,'trapezoid_budget_residual_kg':a[-1]['mass_kg']-a[0]['mass_kg']+integrated,'backward_euler_budget_pct_of_inlet':stats(be),'BDF2_budget_pct_of_inlet':stats(bdf2),'interpretation':'Diagnostic residuals include accumulation. Confirm actual VOF/mixture time formulation; no automatic configuration or mesh acceptance.'}
def main():
 own=P/'controller.lock';lock=R/'queue.lock';claimed=False
 with own.open('x') as f:json.dump({'pid':os.getpid(),'created_at':e.stamp()},f)
 try:
  while True:
   if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():state('paused_by_marker');return
   t=e.read(R/'temporal_validation_state.json',{})
   if t.get('status')=='needs_review':state('waiting_for_temporal_review');return
   if t.get('status')=='completed_screen' and not lock.exists():break
   state('waiting_for_temporal_tests',reason='T01–T04 retain GPU priority');time.sleep(30)
  data=e.read(R/'temporal_validation_results.json',{});cases={x['id'].split('_')[0]:x for x in data.get('cases',[])}
  if set(cases)!=set(['T01','T02','T03','T04']) or not all(x['settling_check_pass'] and x['source_unchanged'] for x in cases.values()):state('needs_review',reason='Temporal windows incomplete or not settled');return
  gate={b:{k:100*(cases[b]['last_window'][k]['mean']/cases['T02']['last_window'][k]['mean']-1) for k in ['CD','CL_total']} for b in ['T03','T04']}
  if any(abs(v)>.25 for g in gate.values() for v in g.values()):state('needs_review',reason='Configuration differences require review before probes',gate=gate);return
  with lock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'Two40-step matched conservation probes'},f)
  claimed=True;ctypes.windll.kernel32.SetThreadExecutionState(0x80000001);e.ROOT=P;e.refresh=refresh;results=[]
  for j in e.read(P/'plan.json')['jobs']:
   if (R/'STOP_ALL').exists() or (P/'STOP_ALL').exists():state('paused_by_marker',results=results);return
   state('starting',active=j['id'],gate=gate);r=e.run_job(j);done=r.get('completed',{})
   if r['returncode']!=0 or done.get('status')!='target_reached' or abs(done.get('time_s',-1)-j['target'])>j['dt']*.1 or not r['original_unchanged']:raise RuntimeError('Probe execution failed: '+j['id'])
   item=summary(j);results.append(item);e.write(P/j['id']/'probe_result.json',item);e.write(R/'conservation_probe_results.json',{'results':results,'updated_at':e.stamp()})
  state('completed_pending_review',results=results,gate=gate)
  e.write(R/'queue_state.json',{'status':'configuration_review','updated_at':e.stamp(),'reason':'Temporal and conservation screens complete; review before M09'})
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  if claimed and e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
  if e.read(own,{}).get('pid')==os.getpid():own.unlink()
  subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
if __name__=='__main__':main()
