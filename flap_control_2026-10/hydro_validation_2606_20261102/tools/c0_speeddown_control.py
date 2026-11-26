"""Start only the prepared, scoped continuation in the existing controller."""
from pathlib import Path
import sys,json
import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks
H=Path(__file__).resolve().parents[1];D=H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103';E='C0_SPEED_DOWN_20261103'
def checks():
 review=q.read(D/'WORK_RESULT.json',{});assert review.get('passed') is True,'20-step native review has not passed'
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 if st.get('active'):
  assert st['active'].get('experiment_id')==E,'Another owned task is active'
  return dict(state='ALREADY_ACTIVE',job=st['active']['id']),cfg,None
 jobs=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]
 if not jobs:return dict(state='HOLD_NO_PENDING_JOB',reason='Completed/failed/paused calculations are not replayed. A pause needs a separately bound continuation checkpoint.'),cfg,None
 assert len(jobs)==1 and jobs[0].get('experiment_id')==E;job=jobs[0]
 assert job['macro']=='C0SpeedDownContinue.java' and job['cpu_processes']==8 and job['angle_deg']==0
 assert not blocks(st,cfg,job),'New scientific failure blocks continuation';launch_integrity(H,job)
 a=q.read(H/'audit/C0_SPEED_DOWN_EXPLICIT_APPROVAL_20261103.json');assert a.get('conditional_continuation_gate_passed') is True
 p=dict(line.split('=',1) for line in (D/'CONTINUATION_RUNTIME.properties').read_text().splitlines() if '=' in line)
 meta=q.read(D/'CONTINUATION_INPUT.json');assert Path(p['input'])==Path(job['input']) and p['sha256']==job['input_sha256']
 for k in ['time_s','iteration']:assert float(p[k])==float(meta[k])
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:assert not (H.parent/name).exists(),'Pause/safety marker remains; no automatic override'
 rs=q.resources();assert rs['ram_available_GiB']>=8 and rs['disk_free_GiB']>=15,'Insufficient resource reserve'
 return dict(state='READY_NOT_RUNNING',job=job['id'],input=job['input'],time_s=job['initial_time_s'],end_time_s=1.05,CPU=8,GPU=False,flap_deg=0,old_failure=st['failure_hold']),cfg,job
def main():
 action=sys.argv[1] if len(sys.argv)>1 else '--check';assert action in ['--check','start']
 info,cfg,job=checks();print(json.dumps(info,indent=2))
 if action!='start' or job is None:return
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);q.event('manual_c0_speeddown_continuation_start',job=job['id'])
 from cfd_control import main as existing
 sys.argv=[sys.argv[0],'start'];return existing()
if __name__=='__main__':
 try:raise SystemExit(main() or 0)
 except AssertionError as e:print('HOLD: '+str(e));raise SystemExit(2)
