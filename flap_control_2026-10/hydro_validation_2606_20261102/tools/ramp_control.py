"""Start only the explicitly approved smooth-ramp continuation, never the failed step case."""
from pathlib import Path
import sys,json,hashlib,datetime
import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks,EXPERIMENT
H=Path(__file__).resolve().parents[1]
def checks():
 review=q.read(H/'audit/RAMP_SMOKE_REVIEW_20261103.json',{});assert review.get('passed') is True,'Ramp smoke not passed'
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 pending=[j for j in cfg['jobs'] if j.get('experiment_id')==EXPERIMENT and j['id'] not in st['jobs'] and not j.get('disabled')]
 if st.get('active'):
  assert st['active'].get('experiment_id')==EXPERIMENT,'Another owned case active'
  return dict(state='ALREADY_ACTIVE',job=st['active']['id']),st,cfg,None
 if not pending:return dict(state='NO_PENDING_JOB',reason='Completed/failed jobs are never repeated automatically'),st,cfg,None
 assert len(pending)==1;job=pending[0]
 assert not blocks(st,cfg,job),'Experiment is blocked by a new failure'
 launch_integrity(H,job);assert job['cpu_processes']==8
 resource=q.resources();assert resource['ram_available_GiB']>=8 and resource['disk_free_GiB']>=15,'Resource reserve insufficient'
 prop=H/'audit/RAMP_PLUS2_RUNTIME.properties';lines=dict(line.split('=',1) for line in prop.read_text().splitlines() if '=' in line)
 assert Path(lines['input'])==Path(job['input']) and abs(float(lines['time_s'])-job['initial_time_s'])<1e-9
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():
   marker=q.read(p);assert marker.get('source')=='cfd_control' and marker.get('reason')=='manual_stop','Safety marker needs review: '+str(p)
 return dict(state='READY',job=job['id'],source=job['input'],time_s=job['initial_time_s'],maximum_time_s=1.25,cpu=8,flow_frozen=False,old_failure_still_blocked=st.get('failure_hold')),st,cfg,job
def main():
 action=sys.argv[1] if len(sys.argv)>1 else '--check'
 assert action in ['--check','start']
 if action=='start':prepare_paused_continuation()
 info,st,cfg,job=checks();print(json.dumps(info,indent=2))
 if action=='--check' or job is None:return
 for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:
  p=H.parent/name
  if p.exists():p.replace(H/'audit'/('ramp_explicit_start_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+name))
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);q.event('explicit_local_ramp_start',job=job['id'])
 from cfd_control import main as existing_control
 sys.argv=[sys.argv[0],'start'];existing_control()
def prepare_paused_continuation():
 # Same approved experiment and law; only a normally paused, verified checkpoint.
 st=q.read(q.STATE);cfg=q.read(q.CFG)
 if st.get('active') or any(j.get('experiment_id')==EXPERIMENT and j['id'] not in st['jobs'] for j in cfg['jobs']):return
 runs=[j for j in st['jobs'].values() if j.get('experiment_id')==EXPERIMENT]
 if not runs:return
 last=max(runs,key=lambda j:j.get('ended_at',''));status=last.get('macro_status') or {}
 if status.get('status')!='ramp_paused':return
 assert st.get('failure_hold')=='plus2_benchmark_8cpu_20261103','New failure requires review'
 cp=Path(last['output'])/'paused_checkpoint.sim';meta=st['checkpoint_integrity'][str(cp)];assert meta['native_save_complete']
 with cp.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 assert digest==meta['sha256'];saved=float(status['saved_time_s']);assert .65<=saved<1.25
 import csv
 with (cp.parent/'history.csv').open() as f:rows=list(csv.DictReader(f))
 prior=dict(line.split('=',1) for line in (H/'audit/RAMP_PLUS2_RUNTIME.properties').read_text().splitlines() if '=' in line)
 iteration=int(rows[-1]['native_iteration']) if rows else int(prior['iteration'])
 macro=H/'macros/RampPlus2Run.java';jid=EXPERIMENT+'_RESUME_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 job=dict(id=jid,kind='ramp',experiment_id=EXPERIMENT,approved=True,macro=macro.name,macro_sha256=hashlib.sha256(macro.read_bytes()).hexdigest(),input=str(cp),input_sha256=digest,initial_time_s=saved,cpu_processes=8,angle_deg=2,progress_timeout_s=900,maximum_runtime_s=7200)
 ap=H/'audit/RAMP_PLUS2_EXPLICIT_APPROVAL_20261103.json';approval=q.read(ap)
 # Macro must be the same compiled implementation reviewed after smoke.
 assert job['macro_sha256']==approval['continued_job']['macro_sha256'],'Continuation macro changed'
 approval['approved_job_ids'].append(jid);q.atomic(ap,approval)
 (H/'audit/RAMP_PLUS2_RUNTIME.properties').write_text(f'input={cp.as_posix()}\ntime_s={saved}\niteration={iteration}\nsha256={digest}\n',encoding='utf8')
 cfg['jobs'].append(job);q.atomic(q.CFG,cfg);q.event('same_ramp_resume_prepared',job=job)
if __name__=='__main__':main()
