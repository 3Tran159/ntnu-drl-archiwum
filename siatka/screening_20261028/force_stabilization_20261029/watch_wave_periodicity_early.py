"""External force-cycle stop policy for the already-running owned continuation."""
import os,json,time
from pathlib import Path
import run_until_settled as e
from wave_cycle_repeatability import evaluate
from manual_control_server import alive
R=Path(__file__).resolve().parent;lock=R/'wave_periodicity_watcher.lock'
def main():
 if lock.exists():raise RuntimeError('Periodicity watcher already registered; inspect before restart.')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='User-corrected early force-repeatability stop'),f)
 try:
  while True:
   state=e.read(R/'wave_foil_run_state.json',{});q=e.read(R/'queue.lock',{});directory=state.get('directory','');case=Path(directory)
   if state.get('case')!='W01_W20L4_M10_FS020_cycles_r2' or q.get('pid')!=state.get('controller_pid') or not alive(q.get('pid')):break
   if state.get('computation_active') is False:break
   if (case/'history.csv').exists():
    policy=e.read(R/'wave_cycle_policy_current.json',{});period=state.get('period_s',.8472673206891129)
    screen=evaluate(['E:/ntnu/quasi2d_waves_20261029/W01_W20L4_M10_FS020_diagnostic_r1/history.csv',str(case/'history.csv')],period,policy['min_cycles'],policy['max_cycles'])
    report=dict(case=case.name,updated_at=e.stamp(),policy_source='wave_cycle_policy_current.json',**screen)
    e.write(R/'wave_periodicity_current.json',report);e.write(case/'periodicity_assessment.json',report)
    if screen['stop_recommended']:
     e.write(case/'periodicity_stop_decision.json',dict(at=e.stamp(),user_policy='No minimum10-cycle wait',screen=screen));(case/'STOP').touch()
     e.write(R/'wave_periodicity_watcher_state.json',dict(status='graceful_stop_requested',case=case.name,at=e.stamp(),reason=screen['stop_reason']))
     break
   time.sleep(10)
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
