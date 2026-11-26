import os,sys,json,time,subprocess,threading,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');A=W/'C01_W20L4_M09_mesh_r1'
import run_until_settled as e
lock=W/'preparation.lock'
def state(status,**kw):e.write(R/'wave_foil_mesh_preparation_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),directory=str(A),scope='M09-derived matched C01/W01 4lambda domain; zero flow steps',**kw))
def main():
 if lock.exists():raise RuntimeError('Another CPU preparation exists')
 if (A/'input_M09.sim').exists():raise RuntimeError('Existing import attempt preserved')
 if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<8*1024**3:raise RuntimeError('Insufficient preparation resources')
 if e.read(R/'selected_mesh_decision.json',{}).get('status')!='supported_calm_mesh_template':raise RuntimeError('Selected calm template missing')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),case=A.name,purpose='CPU1 long-domain mesh import and quality audit'),f)
 try:
  source=R.parent/'quasi2d_012_20261029/M09/mesh.sim';shutil.copy2(source,A/'input_M09.sim')
  digest=e.digest(source);mesh_digest=e.digest(A/'mesh.CGNS')
  if e.digest(A/'input_M09.sim')!=digest:raise RuntimeError('Source copy mismatch')
  e.write(A/'source_identity.json',dict(source_sim=str(source),source_sha256=digest,copied_sha256=digest,input_mesh_sha256=mesh_digest,flow_steps=0))
  state('import_and_quality_audit_CPU',workers=1,gpu=False)
  with (A/'import_star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-batch',str(A/'FinalizeC01W20L4.java'),str(A/'input_M09.sim')],cwd=str(A),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(A/'process.json',dict(launcher_pid=p.pid,workers=1,gpu=False))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   try:rc=p.wait(timeout=1200)
   except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned import/audit timeout')
   th.join(10)
  if rc:raise RuntimeError('STAR import/audit failed')
  P='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe'
  q=subprocess.run([P,str(A/'audit_imported_topology.py'),str(A)],capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
  (A/'topology_audit.log').write_bytes(q.stdout+b'\n'+q.stderr)
  if q.returncode:raise RuntimeError('Independent imported topology audit failed')
  top=e.read(A/'topology_audit.json',{});met=e.read(A/'measurement.json',{}).get('metrics',{})
  preserved=e.digest(source)==digest and e.digest(A/'input_M09.sim')==digest and e.digest(A/'mesh.CGNS')==mesh_digest
  if not preserved or met.get('cell_count')!=246885 or any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5 or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError('Mesh acceptance diagnostics need review')
  result=dict(status='mesh_prepared_pending_boundary_and_flow_setup',source_unchanged=preserved,metrics=met,topology=top,flow_steps=0,source_sim=str(A/'mesh.sim'),pending=['Audit actual boundary areas/bounds and wave-zone length settings','Set matched calm and FifthOrder cases explicitly','Short startup/propagation and wave timestep/domain checks'])
  e.write(A/'controller_result.json',result);state('mesh_prepared_pending_boundary_and_flow_setup',result=result)
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
