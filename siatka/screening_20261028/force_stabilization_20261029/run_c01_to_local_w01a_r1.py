"""One-shot C01->recipe audit->queued W01a handoff. No extra STAR while current C01 runs."""
from pathlib import Path
import os,sys,time,subprocess,uuid,json
import local_control_model as m
import local_control_worker as w
import run_until_settled as e
R=m.R;W=m.W;D=m.D;LOCK=R/'local_recipe_handoff_r1.lock';STATE=R/'local_recipe_handoff_state.json'
def state(status,**kw):m.write(STATE,dict(status=status,pid=os.getpid(),updated_at=m.stamp(),**kw))
def cancelled(job):return (D/'PAUSE').exists() or (R/'STOP_ALL').exists() or (D/'jobs'/job['id']/'CANCEL').exists() or m.read(D/'jobs'/job['id']/'job.json').get('status')=='cancelled'
def main():
 if sys.argv[1:]!=['--run']:raise ValueError('Use --run')
 token=uuid.uuid4().hex;job=None
 if LOCK.exists() or (R/'local_recipe_handoff_r1.consumed').exists():raise RuntimeError('One-shot handoff already used; never restart')
 if any(j.get('status') in ('queued','waiting','running','preparing') for j in m.jobs()):raise RuntimeError('Existing user queue; leave it unchanged')
 with LOCK.open('x') as f:json.dump(dict(pid=os.getpid(),token=token,purpose='Wait for savedC01 then finalize localrecipe andstartqueuedW01a'),f)
 try:
  with (R/'local_recipe_handoff_r1.consumed').open('x') as f:f.write(m.stamp())
  raw=dict(name='W01a',height_m=.5,wavelength_m=20,upstream_m=35,downstream_m=43.81,wall_minutes=180,action='run')
  job=m.enqueue(raw);start=time.monotonic()
  state('waiting_for_C01',job=job['id'],message='C01 continues; no extra CPU/GPU work. Queued W01a can be cancelled or queuepaused fromdashboard.')
  while True:
   if cancelled(job):state('cancelled_or_paused',job=job['id']);return
   source=m.registered_calm(job['spec'],verify=False)
   if not (R/'queue.lock').exists() and not (W/'preparation.lock').exists():
    if source and w.safe_ready():break
    live=m.read(R/'wave_foil_run_state.json')
    if not source and live.get('case')=='C01_W20L4_M10_calm_settle_r2' and live.get('computation_active') is False:raise RuntimeError('C01 stopped without a verified reusable checkpoint')
   if time.monotonic()-start>4*3600:raise RuntimeError('C01 wait limit reached; no extra calculation started')
   time.sleep(5)
  source=m.registered_calm(job['spec'],verify=True)
  if not source:raise RuntimeError('SettledC01 identity check failed')
  if cancelled(job):state('cancelled_or_paused',job=job['id']);return
  audit_dir=W/'LOCAL_INLET_RECIPE_CPU_AUDIT_r2'
  if audit_dir.exists():raise RuntimeError('AuditR2 alreadyexists; inspect, never rerun')
  state('zero_step_recipe_audit',job=job['id'],source=source['file'],source_time_s=source['physical_time_s'],message='C01 saved; oneCPU/noGPU zero-stepAPIcheck. No transientwave yet.')
  with (R/'local_recipe_audit_r2.stdout.log').open('x') as out,(R/'local_recipe_audit_r2.stderr.log').open('x') as err:
   proc=subprocess.Popen([sys.executable,str(R/'audit_local_inlet_recipe_r2.py')],cwd=R,env=dict(os.environ,NTNU_HANDOFF_JOB=job['id']),stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   rc=proc.wait()
  if rc:raise RuntimeError('Zero-stepAPIaudit failed; preservedattempt, no wave launched')
  if cancelled(job):state('cancelled_or_paused_after_audit',job=job['id']);return
  if not m.readiness()['ready']:raise RuntimeError('Recipe/test identity no longer matches; review beforelaunch')
  deadline=time.monotonic()+180
  while not w.safe_ready():
   if cancelled(job):state('cancelled_or_paused',job=job['id']);return
   if time.monotonic()>deadline:raise RuntimeError('An ownsolver remains afteraudit; do not launchduplicate')
   time.sleep(3)
  with m.job_transition(job['id']):
   if cancelled(job):state('cancelled_or_paused_before_start',job=job['id']);return
   result=m.start_worker(resume=False)
  state('handed_to_local_worker',job=job['id'],worker=result,message='W01a queued fromverifiedsettledC01; full inletheight,no ramp. Localworkerownsallfurtherguarding/saves.')
 except BaseException as ex:
  if job and not cancelled(job):
   j=m.read(D/'jobs'/job['id']/'job.json');j.update(status='needs_review',message=e.redact(str(ex)),updated_at=m.stamp());m.write(D/'jobs'/job['id']/'job.json',j)
  D.mkdir(exist_ok=True);(D/'PAUSE').touch();state('needs_review',error=e.redact(str(ex)),job=job['id'] if job else None)
  raise
 finally:
  if m.read(LOCK).get('token')==token:LOCK.unlink()
if __name__=='__main__':main()
