"""Build M09 on two CPU workers; record a verified candidate without starting a GPU job."""
import concurrent.futures,datetime,json,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(R.parent/'night_20261028'))
from night_queue import free_memory
PLOT=r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\python\python.exe'
def read(p,d=None):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return d
def write(p,obj):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');tmp.replace(p)
def run(cmd,log,timeout):
 p=subprocess.run(cmd,capture_output=True,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 log.write_bytes(p.stdout+b'\n'+p.stderr)
 if p.returncode:raise RuntimeError(log.name+' failed; inspect log')
def build(c):
 name=c['id'];raw=Q/(name+'_build');out=Q/name
 if raw.exists() or out.exists():raise RuntimeError(name+': existing attempt preserved')
 if free_memory()<24*1024**3:raise RuntimeError('Need 24 GiB available to add CPU mesh job')
 allocate_directories(name,raw,out);shutil.copy2(Q/'M03/mesh.sim',raw/'input_M03_copy.sim')
 ref=c['linear_refinement'];base=c.get('outer_base_m',.2/ref);first=c['first_layer_um']*1e-6;layers=c['layers']
 design={**c,'purpose':c['purpose'],'total_prism_m':.01546,'base_m':base,'foil_target_m':.004/ref,'foil_min_m':.0004/ref,'global_min_m':.0005/ref,'near_foil_m':.0125/ref,'free_surface_m':.04/ref}
 write(out/'design.json',design);write(raw/'build_status.json',{'status':'meshing','started_at':datetime.datetime.now().astimezone().isoformat()})
 macro=(R/'MeshQ2DM04.java').read_text()
 macro=macro.replace('MeshQ2DM04','MeshRaw'+name).replace('20261029/M04','20261029/'+name+'_build').replace('AuditQ2DM04.java','AuditRaw'+name+'.java')
 macro=macro.replace('double base=.4/2.0;',f'double base={base};').replace('.0005/base',f'{.0005/ref}/base')
 macro=macro.replace('setValue(.000003)',f'setValue({first})').replace('setNumLayers(40)',f'setNumLayers({layers})')
 macro=macro.replace('.008/2.0/base',f'{.004/ref}/base').replace('.0008/2.0/base',f'{.0004/ref}/base').replace('.025/2.0/base',f'{.0125/ref}/base').replace('.08/2.0/base',f'{.04/ref}/base')
 macro=macro.replace(r'\"prism_layers\":40',r'\"prism_layers\":'+str(layers))
 macro=macro.replace(r'\"first_layer_m\":0.000003',r'\"first_layer_m\":'+str(first))
 macro=macro.replace(r'\"linear_refinement_ratio\":\"+2.0+',r'\"linear_refinement_vs_M04\":\"+'+str(ref)+'+')

 middle='''SimpleBlockPart middle=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());
middle.setPresentationName("Q2D_protected_middle_M09");
middle.setCorners(new DoubleVector(new double[]{-11.9,-.1,-3}),new DoubleVector(new double[]{30.94,.1,3.2}));
middle.rebuildSimpleShapePart();
VolumeCustomMeshControl protection=auto.getCustomMeshControls().createVolumeControl();
protection.setPresentationName("Q2D_protected_middle_M09");protection.getGeometryObjects().setObjects(middle);
for(Object v:protection.getCustomConditions().getChildren())if(v instanceof VolumeControlBase)((VolumeControlBase)v).setVolumeControlBaseSizeOption(true);
protection.getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.14285714285714288/base*100);
'''
 anchor='for(DirectedMeshPartCollection pc:'
 if macro.count(anchor)!=1:raise RuntimeError('Unexpected base macro; no modification performed')
 macro=macro.replace(anchor,middle+anchor)
 macro_path=R/('MeshRaw'+name+'.java');macro_path.write_text(macro)
 audit=(R/'AuditQ2DM04.java').read_text().replace('AuditQ2DM04','AuditRaw'+name).replace('20261029/M04','20261029/'+name+'_build').replace('"M04"','"'+name+'_build"')
 (R/('AuditRaw'+name+'.java')).write_text(audit)
 job={'source':str(raw/'input_M03_copy.sim'),'macro':str(macro_path),'log':str(raw/'mesh_build.log'),'np':2,'timeout_s':3600}
 jp=raw/'mesh_job.json';write(jp,job)
 run([sys.executable,str(Q/'run_job.py'),str(jp)],raw/'mesh_runner.log',3900)
 if read(raw/'mesh_build.exit.json',{}).get('returncode')!=0:raise RuntimeError(name+': native meshing failed')
 cells=read(raw/'measurement.json',{}).get('metrics',{}).get('cell_count',0)
 if not 10000<cells<2000000:raise RuntimeError('Cell count outside resource limit')
 write(raw/'build_status.json',{'status':'exact_extrusion','cells':cells})
 run([PLOT,str(R/'exact_extrusion.py'),str(raw/'mesh.CGNS'),str(raw/'mesh_exact.CGNS')],raw/'extrusion.log',600)
 shutil.copy2(raw/'mesh.sim',out/'input_raw_copy.sim')
 final=(R/'FinalizeM04.java').read_text().replace('FinalizeM04','Finalize'+name).replace('20261029/M04_verified','20261029/'+name).replace('138468',str(cells)).replace('AuditVerifiedM04.java','AuditFinal'+name+'.java')
 final=final.replace('Files.createDirectories(out);','Files.createDirectories(out);\ns.getImportManager().importMeshFiles(List.of("'+(raw/'mesh_exact.CGNS').as_posix()+'"));')
 final=final.replace('s.saveState(out.resolve("clean_import.sim").toString());','''for(star.base.report.Report rep:s.getReportManager().getObjects()){
 if(rep instanceof ForceReport){((ForceReport)rep).getParts().setObjects(fresh.getBoundaryManager().getBoundary("HF_012_wall"));((ForceReport)rep).setRepresentation(fv);}
 if(rep instanceof star.base.report.MaxReport && rep.getPresentationName().equals("Maximum Velocity")){((star.base.report.MaxReport)rep).getParts().setObjects(fresh);((star.base.report.MaxReport)rep).setRepresentation(fv);}
}
s.saveState(out.resolve("clean_import.sim").toString());''')
 (R/('Finalize'+name+'.java')).write_text(final)
 audit=(R/'AuditQ2DM04.java').read_text().replace('AuditQ2DM04','AuditFinal'+name).replace('20261029/M04','20261029/'+name).replace('"M04"','"'+name+'"')
 (R/('AuditFinal'+name+'.java')).write_text(audit)
 jp=raw/'finalize_job.json';write(jp,{'source':str(out/'input_raw_copy.sim'),'macro':str(R/('Finalize'+name+'.java')),'log':str(raw/'finalize.log'),'np':2,'timeout_s':1800})
 run([sys.executable,str(Q/'run_job.py'),str(jp)],raw/'finalize_runner.log',2100)
 if read(raw/'finalize.exit.json',{}).get('returncode')!=0:raise RuntimeError(name+': import/physics transfer failed')
 run([PLOT,str(R/'audit_refinement_topology.py'),name],out/'topology_audit.log',600)
 met=read(out/'measurement.json',{}).get('metrics',{});top=read(out/'topology_audit.json',{})
 if any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError(name+': final validity audit failed')
 if met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5:raise RuntimeError(name+': low quality needs review')
 shutil.copy2(raw/'mesh_exact.validation.json',out/'extrusion_validation.json')
 write(out/'mesh_build.exit.json',{'returncode':0,'cells':cells,'exact_extrusion':True,'source_mesh':'M03','family_reference':'M04'})
 write(raw/'build_status.json',{'status':'verified','cells':cells})
 return {**c,'cells':cells}

def allocate_directories(name,raw,out):
 if name!='M09':raise RuntimeError('This build is only authorized for the specified M08 design')
 storage=Path('E:/ntnu/mesh_builds_20261029')
 if shutil.disk_usage('E:/').free<12*1024**3:raise RuntimeError('Less than12GiB on E')
 if raw.parent.resolve()!=Q.resolve() or out.parent.resolve()!=Q.resolve():raise RuntimeError('Unexpected junction parent')
 targets=[storage/(name+'_build'),storage/name]
 for target in targets:
  if target.resolve().parent!=storage.resolve() or target.exists():raise RuntimeError('Existing or unexpected storage target')
 storage.mkdir(parents=True,exist_ok=True)
 for link,target in zip([raw,out],targets):
  target.mkdir()
  p=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  if p.returncode or not link.is_junction() or link.resolve()!=target.resolve():raise RuntimeError('Junction creation/verification failed; preserve all partial files')

def main():
 import os,csv,statistics,math
 own=R/'M09_build.lock'
 if own.exists():raise RuntimeError('Existing M09 build controller; inspect before recovery')
 with own.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'M09 two-CPU build, no GPU launch'},f)
 try:
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'waiting_for_small_wave_audit','started_at':datetime.datetime.now().astimezone().isoformat()})
  audit=Path('E:/ntnu/quasi2d_waves_20261029/W20_H16_X4_audit_r4.exit.json')
  until=time.time()+900
  while not audit.exists():
   if time.time()>until:raise RuntimeError('Wave audit has not exited; preserve CPU preparation limit')
   time.sleep(10)
  if (R/'STOP_ALL').exists():raise RuntimeError('Campaign pause marker present')
  for mesh,folder in [('M08','M08_until_settled_r3'),('M07','M07_until_settled_r1')]:
   result=read(R/folder/'controller_result.json',{})
   if result.get('status')!='completed' or not result.get('original_unchanged'):raise RuntimeError('Reference not accepted: '+mesh)
  pairs=read(R/'M08_M07_comparison.json',{})
  if not pairs.get('both_force_coefficients_within_1pct'):raise RuntimeError('M08/M07 coefficient agreement gate failed')
  c={'id':'M09','family':'low_yplus','reference':'M08','linear_refinement':1.4,'outer_base_m':.25,'first_layer_um':1.530612244897959,'layers':48,'total_prism_m':.01546,'surface_and_outer_match':'M08 surface, near-foil and free-surface controls; remote outer base changed','prism_match':'M07/M08','protected_middle_size_m':.14285714285714288,'protected_middle_xz_m':[-11.9,30.94,-3,3.2],'purpose':'Coarsen remote domain only; protect middle region and preserve M08 foil/prisms/near-foil/FS targets.'}
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'building_on_two_CPU','started_at':datetime.datetime.now().astimezone().isoformat(),'design':c})
  result=build(c)
  write(R/'M09_build_result.json',{'status':'verified_ready_pending_temporal_review','cells':result['cells'],'design':c,'updated_at':datetime.datetime.now().astimezone().isoformat(),'gpu_launched':False})
  write(R/'M09_build_controller.json',{'pid':os.getpid(),'status':'verified_ready_pending_temporal_review','cells':result['cells']})
  print(json.dumps({'M09_cells':result['cells'],'gpu_launched':False}),flush=True)
 except BaseException as ex:
  write(R/'M09_build_result.json',{'status':'needs_review','error':str(ex),'updated_at':datetime.datetime.now().astimezone().isoformat()});raise
 finally:
  if read(own,{}).get('pid')==os.getpid():own.unlink()
  subprocess.run([sys.executable,str(R/'update_status.py')],capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
if __name__=='__main__':main()
