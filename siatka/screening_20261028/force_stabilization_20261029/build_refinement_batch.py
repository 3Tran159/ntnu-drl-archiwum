"""Build and audit M06/M07 on CPU, then admit only valid meshes to the GPU queue."""
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
 raw.mkdir();out.mkdir();shutil.copy2(Q/'M03/mesh.sim',raw/'input_M03_copy.sim')
 ref=c['linear_refinement'];base=.2/ref;first=c['first_layer_um']*1e-6;layers=c['layers']
 design={**c,'purpose':'Systematic refinement of the low-y+ M04 family','total_prism_m':.01546,'base_m':base,'foil_target_m':.004/ref,'foil_min_m':.0004/ref,'global_min_m':.0005/ref,'near_foil_m':.0125/ref,'free_surface_m':.04/ref}
 write(out/'design.json',design);write(raw/'build_status.json',{'status':'meshing','started_at':datetime.datetime.now().astimezone().isoformat()})
 macro=(R/'MeshQ2DM04.java').read_text()
 macro=macro.replace('MeshQ2DM04','MeshRaw'+name).replace('20261029/M04','20261029/'+name+'_build').replace('AuditQ2DM04.java','AuditRaw'+name+'.java')
 macro=macro.replace('double base=.4/2.0;',f'double base={base};').replace('.0005/base',f'{.0005/ref}/base')
 macro=macro.replace('setValue(.000003)',f'setValue({first})').replace('setNumLayers(40)',f'setNumLayers({layers})')
 macro=macro.replace('.008/2.0/base',f'{.004/ref}/base').replace('.0008/2.0/base',f'{.0004/ref}/base').replace('.025/2.0/base',f'{.0125/ref}/base').replace('.08/2.0/base',f'{.04/ref}/base')
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
def main():
 plan=read(R/'mesh_selection_plan.json');candidates=plan['next_candidates']
 topology=(Q/'audit_topology.py').read_text().replace('for _ in range(40):','for _ in range(80):')
 (R/'audit_refinement_topology.py').write_text(topology)
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(build,c):c for c in candidates}
  for future in concurrent.futures.as_completed(futures):
   c=futures[future]
   try:
    result=future.result();results.append({'id':c['id'],'status':'verified','cells':result['cells']})
    jobs=read(R/'mesh_selection_jobs.json',[]);name=c['id']
    if not any(j['id'].startswith(name+'_') for j in jobs):
     jobs.append({'id':name+'_until_settled_r1','source':str(Q/name/'mesh.sim'),'start':0,'cells':result['cells'],'initialize':True,'dt':.001,'inner':20,'order':'FIRST_ORDER','target':10,'wall_budget_s':10800,'termination':'First passing evaluation of both mean changes below 0.5%'})
     jobs.sort(key=lambda j:int(j['id'][1:3]));write(R/'mesh_selection_jobs.json',jobs)
    registry=read(R/'campaign_registry.json',{})
    if not any(x['id']==name for x in registry['cases']):
     registry['cases'].append({'id':name,'role':'Low-y+ refinement of M04','first_layer_um':c['first_layer_um'],'layers':c['layers'],'refinement':c['linear_refinement'],'gpu':'Queued after mesh audit','family':'low_yplus'})
     write(R/'campaign_registry.json',registry)
   except Exception as e:results.append({'id':c['id'],'status':'needs_review','error':str(e)})
   write(R/'refinement_build_results.json',results);print(json.dumps(results[-1]),flush=True)
if __name__=='__main__':main()
