"""Manual controls for the existing serial queue; never terminates a process."""
from pathlib import Path
import sys,json,datetime,shutil
import night_queue as q
H=Path(__file__).resolve().parents[1];R=H.parent
def live(lock,plist):return any(p['pid']==lock.get('pid') and (not lock.get('born') or p['born']==lock['born']) for p in plist)
def snapshot():
 st=q.read(H/'NIGHT_QUEUE_STATE.json',{});cfg=q.read(H/'NIGHT_QUEUE.json',{});plist=q.processes();lock=q.read(H/'audit/night_queue.lock',{});running=live(lock,plist)
 cache=st.get('checkpoint_integrity',{});cp=max(cache.values(),key=lambda x:x.get('hash_at',''),default=None)
 pending=[j['id'] for j in cfg.get('jobs',[]) if j['id'] not in st.get('jobs',{}) and not j.get('disabled')]
 stored=q.read(H/'NIGHT_STATUS.json',{});active=st.get('active');owned=any(p['ownedBatch'] for p in plist)
 solver=stored.get('solver_state','STOPPED') if active and owned else 'STOPPED'
 selected=active or next((j for j in cfg.get('jobs',[]) if j['id'] in pending),None)
 from ramp_authorization import blocks
 held=blocks(st,cfg,selected)
 return dict(at=q.now(),controller_running=running,controller_pid=lock.get('pid') if running else None,solver_state=solver,operation=solver,scientific_state='HOLD' if held else 'AUTHORIZED_EXECUTION_NOT_SCIENTIFIC_VALIDATION',active=active,failure_hold=st.get('failure_hold'),accept_new_jobs=cfg.get('accept_new_jobs'),pending=pending,last_checkpoint=cp,resources=q.resources(),maximum_cpu=8 if selected and selected.get('experiment_id') in ['RAMP_C0_PLUS2_S5_20261103','SPEED_SWEEP_PLUS2_20261103'] else 16,gpu=False),st,cfg
def main():
 action=sys.argv[1].lower() if len(sys.argv)>1 else 'status';assert action in ['start','stop','resume','status']
 info,st,cfg=snapshot()
 if action=='status':print(json.dumps(info,indent=2));return 0
 if action=='stop':
  cfg.update(accept_new_jobs=False,controller_exit_requested=True);q.atomic(q.CFG,cfg)
  marker=R/'STOP_OWNED_CFD.json'
  if not marker.exists():q.atomic(marker,dict(source='cfd_control',reason='manual_stop',at=q.now()))
  q.event('manual_stop_requested',active_job=(st.get('active') or {}).get('id'))
  print('STOP requested: no new jobs; owned macro saves at its next safe step boundary. No force kill. Check STATUS before shutdown.');return 0
 if action=='resume':
  failure=st.get('failure_hold')
  if failure and not cfg.get('release_failure_hold',{}).get(failure):
   print('HOLD: scientific failure is unreleased. RESUME cannot waive it or replay the failed case. '+failure);return 2
  if st.get('active'):
   print('Existing active job must be adopted by START/STATUS; RESUME will not duplicate it.');return 2
  pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled') and j.get('approved')]
  if not pending:print('HOLD: no approved pending jobs. Completed jobs will not be repeated.');return 0
  from queue_safety import launch_integrity
  for j in pending:launch_integrity(H,j)
  for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
   marker=R/name
   if marker.exists():
    data=q.read(marker,{})
    if data.get('source')!='cfd_control' or data.get('reason')!='manual_stop':
     print('HOLD: safety/relocation marker requires explicit review: '+str(marker));return 2
  for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
   marker=R/name
   if marker.exists():shutil.move(str(marker),str(H/'audit'/('resumed_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+name)))
  cfg['accept_new_jobs']=True
 cfg['controller_exit_requested']=False;q.atomic(q.CFG,cfg)
 if info['controller_running']:print('Existing controller adopted; no second controller started.');return 0
 console=H/'runs'/('controller_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.log')
 sys.stdout=console.open('a',encoding='utf8',buffering=1);sys.stderr=sys.stdout
 # Foreground lifetime is intentionally retained. START_CFD.cmd opens this hidden.
 q.main();return 0
if __name__=='__main__':raise SystemExit(main())
