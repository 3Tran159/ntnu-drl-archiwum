"""Prepare audited M10 free-surface grid on matched80m domain; CPU1, zero flow."""
import os,sys,shutil,subprocess,threading,json,time
from pathlib import Path
import run_until_settled as e
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';W=Path('E:/ntnu/quasi2d_waves_20261029')
S=Q/'M10_FS020_r1';A=W/'C01_W20L4_M10_FS020_mesh_r2';B=W/'C01_W20L4_M09_mesh_r1';lock=W/'preparation.lock'
P='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe'
def state(status,**kw):e.write(R/'wave_fs_extension_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),directory=str(A),workers=1,gpu=False,scope='M10 wave free-surface refinement extended80m; no flow admission',**kw))
def main():
 if lock.exists():raise RuntimeError('CPU preparation owner exists')
 if A.exists():raise RuntimeError('Existing extension attempt preserved')
 if (R/'STOP_ALL').exists():raise RuntimeError('Stop marker')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<12*1024**3:raise RuntimeError('Insufficient CPU preparation resources')
 build=e.read(R/'wave_fs_refinement_result.json',{})
 top=e.read(S/'topology_audit.json',{})
 if build.get('status')!='short_domain_mesh_audited_pending_extension' or not build.get('source_unchanged') or not top.get('single_layer_topology') or top.get('foil_edges')!=856:raise RuntimeError('M10 source build gate')
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Wave free-surface M10 long-domain CPU1 extension; no GPU',case=A.name),f)
 try:
  source=S/'mesh.sim';mesh=S/'mesh.CGNS'
  if not source.is_file() or not mesh.is_file():raise RuntimeError('Verified source files missing')
  A.mkdir();digest=e.digest(source);md=e.digest(mesh)
  extender=(R/'extend_m09_wave_domain.py').read_text().replace('M09-derived','M10-FS020-derived').replace("'source_mesh':'M09'","'source_mesh':'M10_FS020_r1'").replace('all M09 source polygons','all M10_FS020 source polygons')
  (A/'extend_m10_wave_domain.py').write_text(extender)
  state('extending_protected_polygons')
  q=subprocess.run([P,str(A/'extend_m10_wave_domain.py'),str(mesh),str(A/'mesh.CGNS'),'-35','45'],capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  (A/'extension.log').write_bytes(q.stdout+b'\n'+q.stderr)
  if q.returncode:raise RuntimeError('Exact extension failed')
  val=e.read(A/'mesh.validation.json',{});cells=val.get('cells',0)
  if val.get('original_cells')!=282379 or not val.get('original_cell_polygons_preserved') or not val.get('original_coordinates_preserved') or val.get('wave_depth_m')!=24 or not 282379<cells<1000000:raise RuntimeError('Extension verification failed')
  final=(B/'FinalizeC01W20L4.java').read_text().replace('FinalizeC01W20L4','FinalizeC01W20L4M10FS').replace('AuditC01W20L4','AuditC01W20L4M10FS').replace(B.as_posix(),A.as_posix()).replace('246885',str(cells))
  (A/'FinalizeC01W20L4M10FS.java').write_text(final)
  audit=(B/'AuditC01W20L4.java').read_text().replace('AuditC01W20L4','AuditC01W20L4M10FS').replace(B.as_posix(),A.as_posix()).replace('C01_W20L4_M09_mesh_r1','C01_W20L4_M10_FS020_mesh_r2')
  (A/'AuditC01W20L4M10FS.java').write_text(audit)
  shutil.copy2(B/'audit_imported_topology.py',A/'audit_imported_topology.py')
  shutil.copy2(source,A/'input_M10.sim')
  if e.digest(A/'input_M10.sim')!=digest:raise RuntimeError('Sourcecopy hash mismatch')
  e.write(A/'source_identity.json',dict(source_sim=str(source),source_sha256=digest,source_mesh=str(mesh),source_mesh_sha256=md,flow_steps=0,remote_dx_limit_m=.2,remote_vertical_spacing='Inherited exactly from refinedM10 inlet/outlet chain; anisotropicstrips,not20mmisotropicremotemesh'))
  state('import_and_quality_audit_CPU',cells=cells)
  with (A/'import_star.log').open('x',encoding='utf-8') as log:
   p=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-batch',str(A/'FinalizeC01W20L4M10FS.java'),str(A/'input_M10.sim')],cwd=str(A),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   e.write(A/'process.json',dict(launcher_pid=p.pid,workers=1,gpu=False))
   def drain():
    for line in p.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   try:rc=p.wait(timeout=1500)
   except subprocess.TimeoutExpired:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned import timeout')
   th.join(10)
  if rc:raise RuntimeError('STAR import failed')
  q=subprocess.run([P,str(A/'audit_imported_topology.py'),str(A)],capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
  (A/'topology_audit.log').write_bytes(q.stdout+b'\n'+q.stderr)
  if q.returncode:raise RuntimeError('Independent topology audit failed')
  top=e.read(A/'topology_audit.json',{});met=e.read(A/'measurement.json',{}).get('metrics',{})
  preserved=e.digest(source)==digest and e.digest(mesh)==md and e.digest(A/'input_M10.sim')==digest
  if not preserved or met.get('cell_count')!=cells or any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5 or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError('Independent geometry/quality gates failed')
  result=dict(status='long_domain_mesh_ready_pending_matched_inputs',updated_at=e.stamp(),cells=cells,source_unchanged=preserved,flow_steps=0,directory=str(A),metrics=met,topology=top,extension=val,pending=['Actual boundary/zone andindependentarea audit','Ownmatchedcalm/W01inputs','Wave propagation,dt andFSsensitivitybeforeforceacceptance'])
  e.write(A/'controller_result.json',result);e.write(R/'wave_fs_extension_result.json',result);state(result['status'],cells=cells,source_unchanged=True,flow_steps=0)
 except BaseException as ex:state('needs_review',error=str(ex));raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
