"""Bounded read-only helper QA. All synthetic state/history is in an isolated temporary folder."""
from pathlib import Path
import csv,io,json,tempfile,os,time,importlib.util
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('qa_arrival_module',R/'wave_arrival_dashboard_panel.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
D=R/'wave_arrival_ui_qa_20261030';D.mkdir(exist_ok=True)
now=time.time();case='W01a_W20L4_M10_inlet_fullheight_restart_r3';target=1.690354445
result={};payloads={}
with tempfile.TemporaryDirectory(prefix='arrival_fixture_',dir=D) as temp:
 folder=Path(temp)/case;folder.mkdir()
 anchor={'case':case,'estimated_targets':{'crest_travel_from_minus34':{'simulation_time_s':target}},'observed_near_inlet_crest':{'gauge_x_m':-34,'time_s':.250},'phase_speed_m_s':23.6053}
 m.ANCHOR=Path(temp)/'anchor.json';m.ANCHOR.write_text(json.dumps(anchor),encoding='utf8')
 def history(t):
  p=folder/'history.csv'
  with p.open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=['time_s','wall_s','step']);w.writeheader()
   for i in range(61):w.writerow({'time_s':t-.060+i*.001,'wall_s':i*1.2,'step':i+100})
  os.utime(p,(now,now))
 def check(name,state,t=.9,done=None,stale=False):
  history(t)
  dp=folder/'completed.json'
  if dp.exists():dp.unlink()
  if done:dp.write_text(json.dumps(done),encoding='utf8')
  if stale:os.utime(folder/'history.csv',(now-200,now-200))
  out=m.forecast(state,now);payloads[name]=out
  result[name]={'status':out['status'],'available':out['available'],'wall_remaining_s':out.get('wall_remaining_s'),'arrival_measured':out.get('arrival_measured'),'view':m.view_values(out)}
  return out
 state={'case':case,'directory':str(folder),'computation_active':True,'progress':{'time_s':.9}}
 a=check('active',state)
 assert a['status']=='forecast' and abs(a['simulation_remaining_s']-(target-.9))<1e-9
 assert abs(a['rate_wall_s_per_simulation_s']-1200)<1e-6 and abs(a['wall_remaining_s']-(target-.9)*1200)<1e-6
 assert a['arrival_measured'] is False
 a=check('paused',{**state,'computation_active':False});assert a['status']=='paused' and a['wall_remaining_s'] is None
 a=check('saving',{**state,'stop_requested':True});assert a['status']=='saving' and a['wall_remaining_s'] is None
 a=check('expired',state,1.8);assert a['status']=='predicted_time_passed' and a['simulation_remaining_s']==0 and a['wall_remaining_s'] is None and a['arrival_measured'] is False
 a=check('wrong_case',{**state,'case':'unrelated_case'});assert a['available'] is False
 a=check('guard_failed',state,done={'status':'stability_guard'});assert a['status']=='guard_failed' and a['wall_remaining_s'] is None
 a=check('stale',state,stale=True);assert a['status']=='stale' and a['wall_remaining_s'] is None
(D/'state_payloads.json').write_text(json.dumps(payloads,indent=2),encoding='utf8')
(D/'state_test_review.json').write_text(json.dumps({'status':'PASS','tests':result,'no_solver_actions':True,'fixtures':'Isolated temporary history only; no production state changed.'},indent=2),encoding='utf8')
print(json.dumps({'status':'PASS','tests':list(result)}))
