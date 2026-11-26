"""Prepare a matched flat-water input from the manually selected mesh; never reuse old fields as settled."""
from pathlib import Path
import json,os,shutil,uuid
import run_until_settled as e
import local_control_model as m
from prepare_campaign_domain import cpu as _cpu,P,Q
R=m.R;W=m.W
def cpu(*a,**kw):
 if (m.D/'PAUSE').exists() or m.hold().get('active'):raise RuntimeError('Queue paused before preparation phase')
 result=_cpu(*a,**kw)
 if (m.D/'PAUSE').exists() or m.hold().get('active'):raise RuntimeError('Queue paused; current preparation saved, no next phase')
 return result
def existing(spec):
 v=m.read(m.D/'domains'/f'{m.domain_key(spec)}.json')
 if v and v.get('mesh_id')==spec['mesh_id'] and v.get('mesh_sha256')==spec['mesh_sha256']:
  p=Path(v.get('path','missing'))
  if p.is_file() and e.digest(p)==v.get('sha256'):return v
 return None
def prepare(spec,jobid,notify):
 key=m.domain_key(spec);A=W/('LOCAL_PREP_'+jobid+'_'+uuid.uuid4().hex[:6]);lock=W/'preparation.lock';root=R/'queue.lock';token=uuid.uuid4().hex
 import local_control_worker as worker
 if not worker.safe_ready() or (R/'STOP_ALL').exists() or m.hold().get('active'):raise RuntimeError('Campaign paused or occupied; no preparation started')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<40*1024**3:raise RuntimeError('Need 24 GiB memory / 40 GiB storage for preparation')
 receipt=m.read(R/'local_mesh_preparation_receipt.json')
 if receipt.get('status')!='javac_passed' or e.digest(R/'PrepareLocalMeshCalm.java')!=receipt.get('macro_sha256'):raise RuntimeError('Selected-mesh preparation macro needs compilation review')
 profile=m.mesh_profile(spec['mesh_id']);source=Path(profile['mesh_sim']);mesh=Path(profile['mesh_cgns'])
 source_sha=e.digest(source);mesh_sha=e.digest(mesh)
 if profile['file_sha256']!=spec['mesh_sha256']:raise RuntimeError('Selected mesh identity differs from queued configuration')
 if source_sha!=profile.get('mesh_sim_sha256',profile['file_sha256']) or mesh_sha!=profile.get('mesh_cgns_sha256'):raise RuntimeError('Inspected mesh files changed; import a new copy')
 env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 G=A/'geometry'
 try:
  worker.own_lock(root,token,A.name);worker.own_lock(lock,token,A.name);A.mkdir()
  m.write(A/'specification.json',spec);notify('Copying the selected mesh; preserving foil and prism coordinates',str(A))
  cpu([P,str(R/'clip_extend_campaign_domain.py'),str(mesh),str(G),str(spec['xmin_m']),str(spec['xmax_m'])],A,'geometry',env,1800)
  cpu([P,str(R/'audit_selected_mesh_domain.py'),str(G)],A,'geometry_audit',env,1800)
  val=m.read(G/'independent_geometry_audit.json');cells=val.get('cells')
  if val.get('status')!='independent_file_geometry_gates_passed_pending_STAR_import' or val.get('source_unchanged') is not True or val.get('foil_coordinates_unchanged') is not True or val.get('negative_or_zero_volumes')!=0 or val.get('source_sha256')!=mesh_sha:raise RuntimeError('Selected-mesh geometry preservation audit failed')
  if not isinstance(cells,int) or not 200000<cells<3000000:raise RuntimeError('Prepared mesh outside supported 0.2-3 million cell range')
  template=W/'C01_W20L4_M09_mesh_r1'
  for src,dst in [('FinalizeC01W20L4.java','FinalizeLocalDomain.java'),('AuditC01W20L4.java','AuditLocalDomain.java')]:
   text=(template/src).read_text().replace('FinalizeC01W20L4','FinalizeLocalDomain').replace('AuditC01W20L4','AuditLocalDomain').replace(template.as_posix(),G.as_posix()).replace('246885',str(cells))
   if src.startswith('Finalize'):
    text=text.replace('if(!inlet.equals("Velocity of Calm"))throw new IllegalStateException("Inlet velocity was not preserved: "+inlet);','')
    text='\n'.join(line for line in text.splitlines() if not line.startswith('String inlet='))
    # Selected mesh may have computed fields. They are explicitly cleared only in the new calm preparation copy.
   (G/dst).write_text(text,encoding='utf8')
  shutil.copy2(source,G/'input_source.sim')
  if e.digest(G/'input_source.sim')!=source_sha:raise RuntimeError('Selected mesh copy mismatch')
  notify('Checking imported mesh quality and one-span topology',str(G))
  cpu([str(e.STAR),*e.saved_options(1),'-batch',str(G/'FinalizeLocalDomain.java'),str(G/'input_source.sim')],G,'import_star',env)
  cpu([P,str(template/'audit_imported_topology.py'),str(G)],G,'topology',env,1800)
  met=m.read(G/'measurement.json').get('metrics',{});top=m.read(G/'topology_audit.json')
  if met.get('cell_count')!=cells or any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5 or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12 or top.get('foil_edges')!=val.get('foil_edges'):raise RuntimeError('STAR geometry gates failed')
  C=A/'CALM';C.mkdir();shutil.copy2(G/'mesh.sim',C/'input.sim');inputsha=e.digest(C/'input.sim')
  shutil.copy2(R/'PrepareLocalMeshCalm.java',C/'PrepareLocalMeshCalm.java')
  ev=dict(env,NTNU_FOIL_PREP_OUT=str(C),NTNU_FOIL_PREP_WAVE='false',NTNU_CFG_HEIGHT='0',NTNU_CFG_LAMBDA=str(spec['wavelength_m']),NTNU_CFG_XMIN=str(spec['xmin_m']),NTNU_CFG_XMAX=str(spec['xmax_m']),NTNU_CFG_ZONE=str(spec['zone_m']),NTNU_CFG_CELLS=str(cells),NTNU_CFG_GAUGES=','.join(map(str,[spec['xmin_m']+1,-1.5,2.5,spec['xmax_m']-1])),NTNU_CFG_DT=str(spec['dt_s']),NTNU_CFG_FOIL_AREA=str(val['foil_boundary_area_m2']),NTNU_CFG_SPAN_AREA=str(val['total_area_m2']))
  notify('Creating a separate flat-water C01 input; zero flow steps',str(C))
  cpu([str(e.STAR),*e.saved_options(1),'-batch',str(C/'PrepareLocalMeshCalm.java'),str(C/'input.sim')],C,'setup_star',ev)
  audit=m.read(C/'initial_audit.json')
  if audit.get('status')!='prepared_zero_steps' or audit.get('flow_steps')!=0 or audit.get('cells')!=cells or audit.get('wave') is not False or audit.get('settings',{}).get('dt_s')!=spec['dt_s'] or e.digest(C/'input.sim')!=inputsha:raise RuntimeError('Calm input preparation audit failed')
  if e.digest(source)!=source_sha or e.digest(mesh)!=mesh_sha:raise RuntimeError('Inspected source changed')
  result=dict(path=str(C/'prepared.sim'),sha256=e.digest(C/'prepared.sim'),physical_time_s=0,cells=cells,audit=str(C/'initial_audit.json'),mesh=str(G/'mesh.CGNS'),mesh_id=spec['mesh_id'],mesh_sha256=spec['mesh_sha256'],domain_key=key,spec=spec,source_unchanged=True,quality=met,topology=top)
  m.write(A/'result.json',result);(m.D/'domains').mkdir(parents=True,exist_ok=True);m.write(m.D/'domains'/f'{key}.json',result)
  return result
 except BaseException as ex:
  if A.exists():m.write(A/'error.json',dict(at=m.stamp(),error=e.redact(str(ex))))
  raise
 finally:worker.release(lock,token);worker.release(root,token)
