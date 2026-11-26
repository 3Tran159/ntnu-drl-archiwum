"""Manual entry into the existing serial queue; never waives a scientific failure."""
from pathlib import Path
import sys,json,hashlib,datetime
import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks
H=Path(__file__).resolve().parents[1];E='SPEED_SWEEP_PLUS2_20261103';OLD='RAMP_C0_PLUS2_S5_20261103_RUN'
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def properties(job,meta):
 p=H/'audit/SPEED_PLUS2_RUNTIME.properties';p.write_text(f'input={Path(job["input"]).as_posix()}\ntime_s={meta["time_s"]}\niteration={meta["iteration"]}\nstage={meta["stage"]}\nstage_start_s={meta["stage_start_s"]}\n',encoding='utf8')
def prepare_paused():
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 if st.get('active') or any(j.get('experiment_id')==E and j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs']):return
 runs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]
 if not runs:return
 last=max(runs,key=lambda x:x.get('ended_at',''))
 if (last.get('macro_status') or {}).get('status')!='speed_paused':return
 assert st.get('failure_hold')==OLD,'A new failure blocks resume'
 cp=Path(last['output'])/'paused_checkpoint.sim';meta=q.read(cp.with_suffix('.sim.json'));assert Path(meta['checkpoint'])==cp and meta['native_save_returned']
 verified=st.get('checkpoint_integrity',{}).get(str(cp),{});assert verified.get('native_save_complete') and verified['sha256']==meta['sha256']==digest(cp)
 ap=H/'audit/SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json';a=q.read(ap);macro=H/'macros/SpeedSweepPlus2Run.java';assert digest(macro)==a['full_run_macro_sha256']
 jid=E+'_RESUME_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 job=dict(id=jid,kind='speed_sweep',experiment_id=E,approved=True,macro=macro.name,macro_sha256=digest(macro),input=str(cp),input_sha256=meta['sha256'],initial_time_s=meta['time_s'],cpu_processes=8,angle_deg=2,progress_timeout_s=900,maximum_runtime_s=86400)
 a['approved_job_ids'].append(jid);q.atomic(ap,a);properties(job,meta);cfg['jobs'].append(job);q.atomic(q.CFG,cfg);q.event('speed_paused_continuation_prepared',job=job,stage=meta['stage'])
def checks():
 review=q.read(H/'audit/SPEED_SMOKE_REVIEW_20261103.json',{});assert review.get('passed') is True,'Native short smoke has not passed; no full sweep allowed'
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 if st.get('active'):
  assert st['active'].get('experiment_id')==E,'Another owned task is active'
  return dict(state='ALREADY_ACTIVE',job=st['active']['id']),st,cfg,None
 pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]
 if not pending:return dict(state='NO_PENDING_JOB',reason='No completed or failed job will be repeated'),st,cfg,None
 assert len(pending)==1 and pending[0].get('experiment_id')==E,'Unexpected queue contents'
 job=pending[0];assert not blocks(st,cfg,job),'Scientific failure blocks launch'
 launch_integrity(H,job);assert job['cpu_processes']==8 and job['macro']=='SpeedSweepPlus2Run.java'
 a=q.read(H/'audit/SPEED_PLUS2_EXPLICIT_APPROVAL_20261103.json');assert job['macro_sha256']==a['full_run_macro_sha256']
 props=dict(line.split('=',1) for line in (H/'audit/SPEED_PLUS2_RUNTIME.properties').read_text().splitlines() if '=' in line)
 meta=q.read(Path(job['input']).with_suffix('.sim.json'))
 assert Path(props['input'])==Path(job['input']) and meta['sha256']==job['input_sha256']
 for k in ['time_s','iteration','stage','stage_start_s']:assert float(props[k])==float(meta[k]),'Runtime state mismatch '+k
 rs=q.resources();assert rs['ram_available_GiB']>=8 and rs['disk_free_GiB']>=15,'Resource reserve insufficient; do not delete protected data'
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():
   m=q.read(p);assert m.get('source')=='cfd_control' and m.get('reason')=='manual_stop','Nonmanual safety marker requires review'
 return dict(state='READY',job=job['id'],input=job['input'],time_s=meta['time_s'],stage=meta['stage'],speeds=[10,12,14,16,18],CPU=8,GPU=False,old_ramp_failure=st.get('failure_hold')),st,cfg,job
def main():
 action=sys.argv[1] if len(sys.argv)>1 else '--check';assert action in ['--check','start']
 if action=='start':prepare_paused()
 info,st,cfg,job=checks();print(json.dumps(info,indent=2))
 if action=='--check' or job is None:return
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():p.replace(H/'audit'/('speed_manual_resume_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+name))
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);q.event('explicit_local_speed_start',job=job['id'])
 from cfd_control import main as existing
 sys.argv=[sys.argv[0],'start'];return existing()
if __name__=='__main__':
 try:raise SystemExit(main() or 0)
 except AssertionError as e:
  print('HOLD: '+str(e));raise SystemExit(2)
