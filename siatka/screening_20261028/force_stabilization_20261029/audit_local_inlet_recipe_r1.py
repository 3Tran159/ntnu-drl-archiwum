"""Unique zero-step CPU recipe audit; no GPU, no flow, no active-state overwrite."""
from pathlib import Path
import os,json,shutil,time,sys
import run_until_settled as e
from prepare_campaign_domain import cpu
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');A=W/'LOCAL_INLET_RECIPE_CPU_AUDIT_r1'
source=W/'W01a_W20L4_M10_calm_start_r1/final.sim';lock=W/'preparation.lock'
if A.exists() or lock.exists():raise RuntimeError('Unique audit or CPU lock already exists')
if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<25*1024**3:raise RuntimeError('Insufficient resources')
sha=e.digest(source)
if sha!='bb2f9004ba8993ed6a7c8401be27b15be56d54d04c7743b15013a8925d9a131d':raise RuntimeError('Source mismatch')
with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Local inlet recipe CPU1 zero-step audit',directory=str(A)),f)
try:
 A.mkdir();shutil.copy2(source,A/'input.sim');shutil.copy2(R/'LocalCalmWave.java',A/'LocalCalmWave.java')
 if e.digest(A/'input.sim')!=sha:raise RuntimeError('Copy mismatch')
 env=dict(os.environ,NTNU_WAVE_OUT=str(A),NTNU_MODE='wave_setup',NTNU_SOURCE_TIME='.587',NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='40000',NTNU_WAVE_CELLS='317277',NTNU_WAVE_HEIGHT='.5',NTNU_WAVE_WALL_S='600',NTNU_CFG_XMIN='-35',NTNU_CFG_XMAX='45',NTNU_CFG_LAMBDA='20',NTNU_CFG_GAUGES='-34,-15.5,-1,2.5,5,25.5,44',NTNU_ZONE='20',OMP_NUM_THREADS='1')
 cpu([str(e.STAR),*e.saved_options(1),'-batch',str(A/'LocalCalmWave.java'),str(A/'input.sim')],A,'audit_star',env,600)
 audit=e.read(A/'prepared_wave_audit.json',{})
 result=dict(at=e.stamp(),audit=audit,source_unchanged=e.digest(source)==sha and e.digest(A/'input.sim')==sha,flow_steps=0,source_is_settled=False,scope='API/field-retention preparation audit only; this diagnostic source is not a settledC01',macro_sha256=e.digest(R/'LocalCalmWave.java'))
 if not result['source_unchanged'] or audit.get('flow_steps')!=0 or audit.get('global_reinitialization')!=False or audit.get('height_m')!=.5 or not (A/'prepared_wave.sim').is_file():raise RuntimeError('Zero-step definition audit failed')
 result['status']='zero_step_API_audit_passed';e.write(A/'controller_result.json',result);e.write(R/'local_control_zero_step_review.json',result)
 print(json.dumps(result))
except BaseException as ex:
 e.write(A/'controller_error.json',dict(error=e.redact(str(ex)),at=e.stamp()));raise
finally:
 if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
