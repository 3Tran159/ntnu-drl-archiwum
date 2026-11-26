"""Unique zero-step CPU domain/input preparation. Never launches GPU or advances flow."""
from pathlib import Path
import json,os,sys,time,subprocess,threading,shutil,datetime
import run_until_settled as e
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';W=Path('E:/ntnu/quasi2d_waves_20261029')
P='E:/Program Files/Siemens/21.02.007-R8/STAR-CCM+21.02.007-R8/star/lib/python/python.exe'
DOMAINS={'L20_X4_M10':(-35,45,20,20),'L20_X3_M10':(-25,35,20,20),'L30_X4_M10':(-52.5,67.5,30,30),'L40_X4_M10':(-70,90,40,40)}
def config(key):
 if key not in DOMAINS:raise ValueError('Unimplemented audited domain preparation: '+key)
 lo,hi,lam,zone=DOMAINS[key];corelo=lo+zone;corehi=hi-zone
 gauges=sorted(set([corelo+.1*lam,-3.,2.5,5.,corehi-.2*lam,corehi-.1*lam]))
 if not all(lo<x<hi and (x< -1 or x>2) for x in gauges):raise ValueError('Unsafe gauge positions')
 return dict(id=key,xmin_m=lo,xmax_m=hi,wavelength_m=lam,zone_m=zone,gauges_m=gauges,mesh='M10_FS020',wave_depth_m=24)
def cpu(cmd,folder,name,env=None,timeout=1800):
 with (folder/(name+'.log')).open('x',encoding='utf8') as log:
  p=subprocess.Popen(cmd,cwd=str(folder),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
  e.write(folder/(name+'_process.json'),dict(pid=p.pid,started_at=e.stamp(),gpu=False,workers=1))
  def drain():
   for line in p.stdout:log.write(e.redact(line));log.flush()
  th=threading.Thread(target=drain,daemon=True);th.start();start=time.time()
  while p.poll() is None:
   if time.time()-start>timeout or e.free_memory()<8*1024**3 or shutil.disk_usage(W).free<12*1024**3 or (R/'STOP_ALL').exists():
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owned zero-step CPU resource/stop/time guard; preserve attempt')
   time.sleep(2)
  th.join(10)
  if p.returncode:raise RuntimeError(name+' failed; inspect preserved redacted log')
def main():
 if len(sys.argv)!=3 or sys.argv[2]!='--run':raise SystemExit('Usage: prepare_campaign_domain.py DOMAIN_ID --run')
 cfg=config(sys.argv[1]);key=cfg['id'];A=W/('CAMPAIGN_INPUT_'+key+'_r1');lock=W/'preparation.lock'
 if A.exists() or lock.exists() or (R/'STOP_ALL').exists():raise RuntimeError('Attempt exists, CPU preparation owned, or stop requested')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<30*1024**3:raise RuntimeError('Insufficient resources')
 receipt=e.read(R/'campaign_macro_build_receipt.json',{})
 if receipt.get('status')!='javac_passed' or e.digest(R/'PrepareCampaignWave.java')!=receipt.get('macros',{}).get('PrepareCampaignWave.java'):raise RuntimeError('Preparation macro compile identity failed')
 source=Q/'M10_FS020_r1'/'mesh.sim';mesh=Q/'M10_FS020_r1'/'mesh.CGNS';top=e.read(Q/'M10_FS020_r1'/'topology_audit.json',{})
 if not top.get('single_layer_topology') or top.get('foil_boundary_edges') not in (None,856):raise RuntimeError('Source topology not passed')
 sha=e.digest(source);md=e.digest(mesh)
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Campaign '+key+' CPU1 zero-step preparation',directory=str(A)),f)
 def state(status,**kw):e.write(R/'campaign_preparation_state.json',dict(status=status,at=e.stamp(),pid=os.getpid(),domain=key,directory=str(A),gpu=False,flow_steps=0,**kw))
 try:
  A.mkdir();e.write(A/'configuration.json',cfg);e.write(A/'source_identity.json',dict(source=str(source),source_sha256=sha,mesh=str(mesh),mesh_sha256=md))
  state('extending_mesh_CPU1')
  env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
  cpu([P,str(R/'extend_m09_wave_domain.py'),str(mesh),str(A/'mesh.CGNS'),str(cfg['xmin_m']),str(cfg['xmax_m'])],A,'extension',env,600)
  val=e.read(A/'mesh.validation.json',{});cells=val.get('cells',0)
  if val.get('original_cells')!=282379 or not val.get('original_cell_polygons_preserved') or not val.get('original_coordinates_preserved') or val.get('wave_depth_m')!=24 or not 282379<cells<1000000:raise RuntimeError('Exact source/extension validation failed')
  B=W/'C01_W20L4_M09_mesh_r1'
  final=(B/'FinalizeC01W20L4.java').read_text().replace('FinalizeC01W20L4','FinalizeCampaignDomain').replace('AuditC01W20L4','AuditCampaignDomain').replace(B.as_posix(),A.as_posix()).replace('246885',str(cells))
  audit=(B/'AuditC01W20L4.java').read_text().replace('AuditC01W20L4','AuditCampaignDomain').replace(B.as_posix(),A.as_posix())
  (A/'FinalizeCampaignDomain.java').write_text(final);(A/'AuditCampaignDomain.java').write_text(audit)
  shutil.copy2(source,A/'input_source.sim')
  if e.digest(A/'input_source.sim')!=sha:raise RuntimeError('Source copy mismatch')
  state('import_quality_CPU1',cells=cells)
  cpu([str(e.STAR),*e.saved_options(1),'-batch',str(A/'FinalizeCampaignDomain.java'),str(A/'input_source.sim')],A,'import_star',env)
  cpu([P,str(B/'audit_imported_topology.py'),str(A)],A,'topology',env,600)
  met=e.read(A/'measurement.json',{}).get('metrics',{});top=e.read(A/'topology_audit.json',{})
  if met.get('cell_count')!=cells or any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5 or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError('Independent STAR quality/topology gate failed')
  outputs={}
  for label,h in [('CALM',0),('H050',.5)]:
   D=A/label;D.mkdir();state('preparing_paired_input_CPU1',input=label,cells=cells)
   shutil.copy2(A/'mesh.sim',D/'input.sim');inputsha=e.digest(A/'mesh.sim')
   if e.digest(D/'input.sim')!=inputsha:raise RuntimeError('Mesh input copy mismatch')
   shutil.copy2(R/'PrepareCampaignWave.java',D/'PrepareCampaignWave.java')
   ev=dict(env,NTNU_FOIL_PREP_OUT=str(D),NTNU_FOIL_PREP_WAVE=str(h>0).lower(),NTNU_CFG_HEIGHT=str(h),NTNU_CFG_LAMBDA=str(cfg['wavelength_m']),NTNU_CFG_XMIN=str(cfg['xmin_m']),NTNU_CFG_XMAX=str(cfg['xmax_m']),NTNU_CFG_ZONE=str(cfg['zone_m']),NTNU_CFG_CELLS=str(cells),NTNU_CFG_GAUGES=','.join(map(str,cfg['gauges_m'])))
   cpu([str(e.STAR),*e.saved_options(1),'-batch',str(D/'PrepareCampaignWave.java'),str(D/'input.sim')],D,'setup_star',ev)
   a=e.read(D/'initial_audit.json',{})
   if a.get('status')!='prepared_zero_steps' or a.get('flow_steps')!=0 or a.get('cells')!=cells or not (D/'prepared.sim').is_file() or e.digest(D/'input.sim')!=inputsha:raise RuntimeError('Independent paired preparation failed')
   outputs[label]=dict(path=str(D/'prepared.sim'),sha256=e.digest(D/'prepared.sim'),cells=cells,audit=str(D/'initial_audit.json'),wave_period_s=a['wave_period_s'],height_m=h)
  if e.digest(source)!=sha or e.digest(mesh)!=md:raise RuntimeError('Original source identity changed')
  result=dict(status='paired_inputs_audited_zero_steps',at=e.stamp(),domain=cfg,cells=cells,directory=str(A),inputs=outputs,source_unchanged=True,flow_steps=0,quality=met,topology=top,pending=['Wave propagation','Wave-specific timestep','Grid sensitivity','Cycle force repeatability and matched calm'])
  e.write(A/'controller_result.json',result);(R/'campaign_inputs').mkdir(exist_ok=True);e.write(R/'campaign_inputs'/(key+'.json'),result);state('paired_inputs_audited_zero_steps',result=str(A/'controller_result.json'))
 except BaseException as ex:
  state('needs_review',error=e.redact(str(ex)));e.write(A/'controller_error.json',dict(error=e.redact(str(ex)),at=e.stamp()));raise
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
