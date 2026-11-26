"""Isolated no-foil short transient check, two CPU workers, no GPU or foil forces."""
import os,sys,json,time,subprocess,threading,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');srcdir=W/'W20_H24_X4_Q2D_r5';case=W/'W20_H24_X4_CPUprop_dt1ms_r1'
sys.path.insert(0,str(R));import run_until_settled as e
lock=W/'preparation.lock'
def state(status,**kw):
 d=dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),workers=2,gpu=False,scope='No-foil short propagation pilot; not force or final propagation validation',**kw)
 e.write(R/'wave_propagation_state.json',d);e.write(R/'wave_preparation_state.json',d)
def main():
 if lock.exists():raise RuntimeError('Another CPU wave task owns the preparation lock')
 with lock.open('x') as f:json.dump({'pid':os.getpid(),'case':case.name,'purpose':'CPU no-foil transient pilot'},f)
 try:
  if (R/'STOP_ALL').exists():state('paused_by_marker');return
  if case.exists():raise RuntimeError('Attempt exists; preserve and use a new ID')
  geo=e.read(srcdir/'topology_audit.json',{});audit=e.read(srcdir/'initial_audit.json',{})
  if geo.get('status')!='geometry_pass' or not geo.get('single_span') or not geo.get('boundary_mapping_valid'):raise RuntimeError('Independent geometry gate not passed')
  gauges=audit.get('initial_gauges',[])
  if len(gauges)!=5 or any(abs(x.get('plane_height_m',0)-30)>1e-5 or abs(x.get('calm_eta_check_m',99))>.03 for x in gauges):raise RuntimeError('Gauge normalization gate not passed')
  height=max(x['eta_actual_m'] for x in gauges)-min(x['eta_actual_m'] for x in gauges)
  if not .45<height<.55 or abs(geo.get('mean_eta_from_volume_m',99))>.02:raise RuntimeError('Initial wave height/mean level gate not passed')
  if audit.get('depth_m')!=24 or audit.get('first_wave_front') is not False:raise RuntimeError('Wave scope mismatch')
  if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Insufficient resources')
  case.mkdir();source=srcdir/'built.sim';shutil.copy2(source,case/'input.sim');shutil.copy2(R/'WavePropagationCheck.java',case/'WavePropagationCheck.java')
  digest=e.digest(source)
  if digest!=e.digest(case/'input.sim'):raise RuntimeError('Source copy mismatch')
  e.write(case/'source_identity.json',{'source':str(source),'source_sha256':digest,'copied_sha256':digest,'geometry_gate':str(srcdir/'topology_audit.json'),'initial_audit':str(srcdir/'initial_audit.json')})
  env=dict(os.environ,NTNU_WAVE_OUT=str(case),NTNU_WAVE_DT='.001',NTNU_WAVE_STEPS='1000',NTNU_WAVE_CELLS=str(audit['cells']))
  start=time.time();state('propagation_CPU_running')
  with (case/'star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(2),'-batch',str(case/'WavePropagationCheck.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(case/'process.json',{'launcher_pid':p.pid,'started_at':e.stamp(),'gpu':False,'workers':2})
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   while p.poll() is None:
    if time.time()-start>3000 or e.free_memory()<12*1024**3 or (R/'STOP_ALL').exists():
     subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError('Owned CPU pilot stopped due resources/timeout/user marker; preserve attempt and checkpoint')
    state('propagation_CPU_running',elapsed_s=time.time()-start,launcher_pid=p.pid,progress=e.read(case/'progress.json',{}))
    time.sleep(15)
   rc=p.wait();th.join(10)
  done=e.read(case/'completed.json',{});preserved=e.digest(source)==digest and e.digest(case/'input.sim')==digest
  result={'returncode':rc,'source_unchanged':preserved,'completed':done,'elapsed_s':time.time()-start}
  e.write(case/'controller_result.json',result)
  if rc or not preserved or done.get('status')!='target_reached' or done.get('steps')!=1000:raise RuntimeError('Pilot incomplete or guard triggered; inspect preserved attempt')
  state('propagation_pilot_complete_pending_review',result=result,next_gate='Check numerical/analytic amplitude, phase, mean level, conservation and direction; pilot is too short for final reflection validation')
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
