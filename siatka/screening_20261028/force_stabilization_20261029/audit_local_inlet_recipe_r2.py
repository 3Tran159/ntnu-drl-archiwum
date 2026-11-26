"""Unique zero-step CPU recipe audit after C01; owns root+preparation locks. Never restart."""
from pathlib import Path
import os,json,shutil,sys,ctypes,uuid
import run_until_settled as e
import local_control_model as m
import local_control_worker as w
from prepare_campaign_domain import cpu
R=m.R;W=m.W;A=W/'LOCAL_INLET_RECIPE_CPU_AUDIT_r2';root=R/'queue.lock';lock=W/'preparation.lock';token=uuid.uuid4().hex
source=W/'W01a_W20L4_M10_calm_start_r1/final.sim'
def check_pause():
 job=os.getenv('NTNU_HANDOFF_JOB','')
 if (m.D/'PAUSE').exists() or (R/'STOP_ALL').exists() or (job and (m.D/'jobs'/job/'CANCEL').exists()):raise RuntimeError('User cancelled/paused before audit phase')
check_pause()
if A.exists() or not w.safe_ready():raise RuntimeError('Unique audit exists or campaign not clear; no CPU/GPU overlap')
if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<25*1024**3:raise RuntimeError('Insufficient resources')
sha=e.digest(source);macro_sha=e.digest(R/'LocalCalmWave.java');receipt=m.read(R/'local_control_macro_receipt.json')
if sha!='bb2f9004ba8993ed6a7c8401be27b15be56d54d04c7743b15013a8925d9a131d' or receipt.get('status')!='javac_passed' or receipt.get('macro_sha256')!=macro_sha:raise RuntimeError('Source/macro identity mismatch')
k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
k.SetProcessAffinityMask(k.GetCurrentProcess(),3);k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
try:
 w.own_lock(root,token,A.name);w.own_lock(lock,token,A.name);check_pause()
 A.mkdir();shutil.copy2(source,A/'input.sim');shutil.copy2(R/'LocalCalmWave.java',A/'LocalCalmWave.java')
 if e.digest(A/'input.sim')!=sha or e.digest(A/'LocalCalmWave.java')!=macro_sha:raise RuntimeError('Copy mismatch')
 env=dict(os.environ,NTNU_WAVE_OUT=str(A),NTNU_MODE='wave_setup',NTNU_SOURCE_TIME='.587',NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='40000',NTNU_WAVE_CELLS='317277',NTNU_WAVE_HEIGHT='.5',NTNU_WAVE_WALL_S='600',NTNU_CFG_XMIN='-35',NTNU_CFG_XMAX='45',NTNU_CFG_LAMBDA='20',NTNU_CFG_GAUGES='-34,-15.5,-1,2.5,5,25.5,44',NTNU_ZONE='20',OMP_NUM_THREADS='1')
 check_pause()
 cpu([str(e.STAR),*e.saved_options(1),'-batch',str(A/'LocalCalmWave.java'),str(A/'input.sim')],A,'audit_star',env,600)
 audit=e.read(A/'prepared_wave_audit.json',{})
 result=dict(at=e.stamp(),audit=audit,source_unchanged=e.digest(source)==sha and e.digest(A/'input.sim')==sha,flow_steps=0,source_is_settled=False,scope='API/field-retention preparation audit only; diagnostic source is not settledC01',macro_sha256=macro_sha)
 if not result['source_unchanged'] or audit.get('flow_steps')!=0 or audit.get('global_reinitialization')!=False or audit.get('height_m')!=.5 or not (A/'prepared_wave.sim').is_file():raise RuntimeError('Zero-step definition audit failed')
 result['status']='zero_step_API_audit_passed';e.write(A/'controller_result.json',result);e.write(R/'local_control_zero_step_review.json',result)
 print(json.dumps(result))
except BaseException as ex:
 if A.exists():e.write(A/'controller_error.json',dict(error=e.redact(str(ex)),at=e.stamp()))
 raise
finally:
 w.release(lock,token);w.release(root,token)
