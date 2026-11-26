from pathlib import Path
import sys,json,hashlib,datetime,shutil
import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks
H=Path(__file__).resolve().parents[1];E='BOUNDED_FIXED_PLUS2_SWEEP_20261103'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def prepare_paused():
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 if st.get('active') or any(j.get('experiment_id')==E and j['id'] not in st['jobs'] and not j.get('disabled') for j in cfg['jobs']):return
 runs=[r for r in st['jobs'].values() if r.get('experiment_id')==E and r.get('output')]
 if not runs:return
 last=max(runs,key=lambda r:r.get('ended_at',''))
 if (last.get('macro_status') or {}).get('status')!='bounded_sweep_paused':return
 marker=H.parent/'STOP_OWNED_CFD.json';m=q.read(marker,{});assert m.get('source')=='cfd_control' and m.get('reason')=='manual_stop','Only manual pause can resume automatically'
 cp=Path(last['output'])/'paused_checkpoint.sim';meta=q.read(cp.with_suffix('.sim.json'));verified=st.get('checkpoint_integrity',{}).get(str(cp),{});assert verified.get('native_save_complete') and meta['sha256']==verified['sha256']==sha(cp)
 assert 0<=int(meta['stage'])<=7 and 10-1e-9<=meta['U_m_s']<=18+1e-9 and 0<=meta['angle_deg']<=2+1e-7
 ap=H/'audit/BOUNDED_SWEEP_APPROVAL_20261103.json';a=q.read(ap);assert st['failure_hold']==a['previous_blocked_job']
 macro=H/'macros/BoundedFixedFlapSweep.java';assert sha(macro)==a['macro_sha256']
 props=H/'audit/BOUNDED_SWEEP_RUNTIME.properties';props.write_text(f'input={cp.as_posix()}\ntime_s={meta["time_s"]}\niteration={meta["iteration"]}\nstage={meta["stage"]}\nstage_start_s={meta["stage_start_s"]}\n',encoding='utf8')
 j={**a['job'], 'id':E+'_RESUME_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),'input':str(cp),'input_sha256':meta['sha256'],'initial_time_s':meta['time_s'],'runtime_properties_sha256':sha(props)}
 a['approved_job_ids'].append(j['id']);q.atomic(ap,a);cfg['jobs'].append(j);q.atomic(q.CFG,cfg);q.event('bounded_manual_pause_resume_bound',job=j)
def checks():
 st=q.read(q.STATE);cfg=q.read(q.CFG);q.validate(cfg)
 if st.get('active'):
  assert st['active'].get('experiment_id')==E,'Another owned task is active'
  return dict(state='ALREADY_ACTIVE',job=st['active']['id']),cfg,None
 pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]
 if not pending:return dict(state='NO_PENDING_APPROVED_JOB',reason='No completed/failed task is replayed'),cfg,None
 assert len(pending)==1 and pending[0].get('experiment_id')==E,'Unexpected queue scope'
 j=pending[0];assert not blocks(st,cfg,j),'A new failure blocks the campaign';launch_integrity(H,j)
 assert j['cpu_processes']==8 and sha(H/'audit/BOUNDED_SWEEP_RUNTIME.properties')==j['runtime_properties_sha256']
 assert not any(p['ownedBatch'] for p in q.processes()),'Existing owned STAR needs adoption'
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():
   m=q.read(p);assert m.get('source')=='cfd_control' and m.get('reason')=='manual_stop','Safety marker needs review'
 rs=q.resources();assert rs['ram_available_GiB']>=8 and rs['disk_free_GiB']>=15,'Insufficient resource reserve'
 return dict(state='READY',job=j['id'],input=j['input'],time_s=j['initial_time_s'],CPU=8,GPU=False,stages='decel10;settle0;flap+2;settle;12,14,16,18',old_failure_preserved=st['failure_hold'],resources=rs),cfg,j
def main():
 action=sys.argv[1] if len(sys.argv)>1 else '--check';assert action in ['--check','start']
 if action=='start':prepare_paused()
 info,cfg,j=checks();print(json.dumps(info,indent=2))
 if action=='--check' or j is None:return
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():p.replace(H/'audit'/('bounded_manual_resume_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+name))
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);q.event('bounded_pipeline_explicit_start',job=j['id'])
 from cfd_control import main as existing
 sys.argv=[sys.argv[0],'start'];return existing()
if __name__=='__main__':
 try:raise SystemExit(main() or 0)
 except AssertionError as e:print('HOLD: '+str(e));raise SystemExit(2)
