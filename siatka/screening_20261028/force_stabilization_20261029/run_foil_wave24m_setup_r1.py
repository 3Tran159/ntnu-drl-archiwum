"""CPU1 zero-step preparation of paired long-domain calm/W01 copies. Never starts flow."""
import os,sys,json,time,subprocess,threading,shutil
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029')
source=W/'C01_W20L4_M09_mesh_r1'/'mesh.sim';lock=W/'preparation.lock'
jobs=[('C01_W20L4_M09_env_setup_r1',False),('W01_W20L4_M09_env_setup_r1',True)]
def state(status,**kw):e.write(R/'wave_foil_case_preparation_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),workers=1,gpu=False,scope='Paired calm/W01 input preparation, zero flow steps; source mesh preserved',**kw))
def main():
 if lock.exists():raise RuntimeError('Existing CPU owner; inspect first')
 if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker')
 mesh=e.read(R/'wave_foil_mesh_preparation_state.json',{}).get('result',{})
 if mesh.get('status')!='mesh_prepared_pending_boundary_and_flow_setup' or not mesh.get('source_unchanged') or not mesh.get('topology',{}).get('single_layer_topology'):raise RuntimeError('Mesh gate not satisfied')
 if e.read(R/'selected_mesh_decision.json',{}).get('status')!='supported_calm_mesh_template':raise RuntimeError('Calm template not selected')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Resource guard')
 if any((W/n).exists() for n,_ in jobs):raise RuntimeError('Attempt exists; preserve and use new IDs')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Paired foil calm/W01 zero-step CPU1 preparation'),f)
 p=None;results=[]
 try:
  for name,waving in jobs:
   if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker before preparation')
   case=W/name;case.mkdir();shutil.copy2(source,case/'input.sim');shutil.copy2(R/'PrepareFoilWave24m.java',case/'PrepareFoilWave24m.java')
   digest=e.digest(source)
   if e.digest(case/'input.sim')!=digest:raise RuntimeError('Copy mismatch')
   e.write(case/'source_identity.json',dict(source=str(source),source_sha256=digest,copy_sha256=digest,source_mesh='M09 extended246885cells',wave=waving,purpose='Preparation only; no flow admission'))
   state('initializing_copy_CPU',case=name,directory=str(case),completed=results)
   env=dict(os.environ,NTNU_FOIL_PREP_OUT=str(case),NTNU_FOIL_PREP_WAVE=str(waving).lower())
   t0=time.time()
   with (case/'star.log').open('x',encoding='utf-8') as log:
    p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-batch',str(case/'PrepareFoilWave24m.java'),str(case/'input.sim')],cwd=str(case),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    e.write(case/'process.json',dict(launcher_pid=p.pid,workers=1,gpu=False))
    def drain():
     for line in p.stdout:log.write(e.redact(line));log.flush()
    th=threading.Thread(target=drain,daemon=True);th.start()
    while p.poll() is None:
     if time.time()-t0>1800 or e.free_memory()<6*1024**3:
      subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned CPU preparation resource/time guard')
     time.sleep(10)
    rc=p.wait();th.join(10)
   audit=e.read(case/'initial_audit.json',{});same=e.digest(source)==digest and e.digest(case/'input.sim')==digest
   result=dict(case=name,directory=str(case),returncode=rc,source_unchanged=same,elapsed_s=time.time()-t0,audit=audit)
   e.write(case/'controller_result.json',result);results.append(result)
   if rc or not same or audit.get('status')!='prepared_zero_steps' or audit.get('flow_steps')!=0:raise RuntimeError('Preparation audit failed; preserve attempt and inspect')
   state('one_copy_prepared',completed=results)
  e.write(R/'wave_foil_case_preparation_results.json',dict(status='paired_inputs_prepared_pending_flow_gates',updated_at=e.stamp(),results=results,flow_admitted=False,pending=['No-foil boundary/propagation validation','Guarded foil startup','Wave-specific dt and FS-resolution checks','Matched calm settling and complete wave cycles']))
  state('paired_inputs_prepared_pending_flow_gates',completed=results)
 except BaseException as ex:
  if p is not None and p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  state('needs_review',error=str(ex),completed=results);raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
