"""Explicit CPU-only, zero-flow recipe validation. Never starts a calm/wave calculation."""
from pathlib import Path
import os,sys,uuid,shutil,json,subprocess,ctypes
import local_control_model as m
import run_until_settled as e
R=m.R;W=m.W
def request():
 if not m.readiness().get('can_validate_recipe'):raise ValueError('Compile and controller tests must pass before recipe inspection')
 import local_control_worker as w
 if not w.safe_ready():raise ValueError('An owned calculation or inspection is active')
 lock=R/'local_recipe_validation.lock'
 if lock.exists():raise ValueError('A recipe inspection is already registered; inspect its saved status')
 folder=m.D/'validation_requests';folder.mkdir(parents=True,exist_ok=True);rid=uuid.uuid4().hex;p=folder/(rid+'.json')
 m.write(p,dict(id=rid,requested_at=m.stamp(),explicit_zero_flow=True))
 with p.with_suffix('.stdout.log').open('x') as out,p.with_suffix('.stderr.log').open('x') as err:
  proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--inspect',str(p)],cwd=R,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
 return dict(message='Zero-step CPU recipe inspection requested. C01 and wave calculations remain paused.',pid=proc.pid)
def main(path):
 import local_control_worker as w
 from prepare_campaign_domain import cpu
 request_path=Path(path).resolve()
 if request_path.parent!=(m.D/'validation_requests').resolve() or not m.read(request_path).get('explicit_zero_flow'):raise RuntimeError('Explicit local inspection request required')
 if not w.safe_ready() or (R/'STOP_ALL').exists():raise RuntimeError('Campaign busy or stop marker present')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<25*1024**3:raise RuntimeError('Need 24 GiB memory and 25 GiB storage for inspection')
 rid=m.read(request_path)['id'];A=W/('LOCAL_RECIPE_CHECK_'+rid);token=uuid.uuid4().hex;locks=[R/'queue.lock',W/'preparation.lock',R/'local_recipe_validation.lock']
 if A.exists():raise RuntimeError('Inspection attempt already exists; never restart it')
 macro=R/'LocalCalmWave.java';macrosha=e.digest(macro);receipt=m.read(R/'local_control_macro_receipt.json')
 source=W/'W01a_W20L4_M10_calm_start_r1/final.sim';expected='bb2f9004ba8993ed6a7c8401be27b15be56d54d04c7743b15013a8925d9a131d'
 if e.digest(source)!=expected or receipt.get('status')!='javac_passed' or receipt.get('macro_sha256')!=macrosha:raise RuntimeError('Recipe/API reference identity mismatch')
 def state(status,**kw):m.write(R/'local_recipe_validation_state.json',dict(status=status,updated_at=m.stamp(),directory=str(A),controller_pid=os.getpid(),flow_steps=0,**kw))
 k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetProcessAffinityMask(k.GetCurrentProcess(),3)
 try:
  for lock in locks:w.own_lock(lock,token,A.name)
  A.mkdir();state('running')
  outcomes=[]
  src=source
  for label,resume in [('new_wave_definition',False),('saved_wave_definition',True)]:
   if (A/'STOP').exists() or (R/'STOP_ALL').exists():raise RuntimeError('Inspection cancelled between zero-step phases')
   B=A/label;B.mkdir();before=e.digest(src);shutil.copy2(src,B/'input.sim');shutil.copy2(macro,B/'LocalCalmWave.java')
   if e.digest(B/'input.sim')!=before:raise RuntimeError('Copied input differs')
   env=dict(os.environ,NTNU_WAVE_OUT=str(B),NTNU_MODE='wave_setup',NTNU_SOURCE_TIME='.587',NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='30',NTNU_WAVE_CELLS='317277',NTNU_WAVE_HEIGHT='.5',NTNU_WAVE_WALL_S='600',NTNU_CFG_XMIN='-35',NTNU_CFG_XMAX='45',NTNU_CFG_LAMBDA='20',NTNU_CFG_GAUGES='-34,-15.5,-1,2.5,5,25.5,44',NTNU_ZONE='20',NTNU_RESUME_WAVE=str(resume).lower(),NTNU_WAVE_ACTIVATION_TIME='.587',NTNU_CHECKPOINT_INTERVAL_S='.05',OMP_NUM_THREADS='1')
   cpu([str(e.STAR),*e.saved_options(1),'-batch',str(B/'LocalCalmWave.java'),str(B/'input.sim')],B,'star',env,900)
   audit=m.read(B/'prepared_wave_audit.json')
   if e.digest(src)!=before or e.digest(B/'input.sim')!=before or audit.get('flow_steps')!=0 or audit.get('global_reinitialization') is not False or audit.get('height_m')!=.5 or abs(audit.get('time_s',-1)-.587)>1e-8 or not (B/'prepared_wave.sim').is_file():raise RuntimeError('Zero-step source/definition check failed')
   outcomes.append(dict(mode=label,audit=audit,source_unchanged=True));src=B/'prepared_wave.sim'
  if e.digest(source)!=expected or e.digest(macro)!=macrosha:raise RuntimeError('Reference/macro changed during inspection')
  result=dict(status='zero_step_API_audit_passed',updated_at=m.stamp(),macro_sha256=macrosha,checks=outcomes,flow_steps=0,directory=str(A),source_unchanged=True,source_is_settled=False,scope='STAR API definition and saved-wave binding check only. No flow, mesh convergence or accuracy acceptance.')
  m.write(A/'controller_result.json',result);m.write(R/'local_control_zero_step_review.json',result);state('passed',message='Both zero-step recipe paths passed; flow remains paused')
 except BaseException as ex:
  if A.exists():m.write(A/'error.json',dict(error=e.redact(str(ex)),updated_at=m.stamp(),flow_steps=0))
  state('failed',error=e.redact(str(ex)));raise
 finally:
  for lock in reversed(locks):w.release(lock,token)
if __name__=='__main__':
 if len(sys.argv)!=3 or sys.argv[1]!='--inspect':raise SystemExit('Use explicit dashboard inspection request')
 try:main(sys.argv[2])
 except BaseException as ex:
  m.write(R/'local_recipe_validation_state.json',dict(status='failed',updated_at=m.stamp(),flow_steps=0,error=e.redact(str(ex))));raise
