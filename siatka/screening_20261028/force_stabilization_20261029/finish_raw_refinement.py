"""Finish an already meshed refinement using the independently checked source extrusion."""
import sys,shutil,json
from pathlib import Path
import build_refinement_batch as b
R=b.R;Q=b.Q
name=sys.argv[1];meshfile=Path(sys.argv[2])
if name not in ['M06','M07','M08','M09','M10']:raise RuntimeError('Unexpected case')
raw=Q/(name+'_build');out=Q/name
c=next(c for c in b.read(R/'mesh_selection_plan.json')['next_candidates'] if c['id']==name)
cells=b.read(meshfile.with_suffix('.validation.json'),{})['cells']
if (out/'mesh.sim').exists():raise RuntimeError('A finalized model already exists')
if not (out/'input_raw_copy.sim').exists():shutil.copy2(raw/'mesh.sim',out/'input_raw_copy.sim')
final=(R/'FinalizeM04.java').read_text().replace('FinalizeM04','FinalizeSource'+name).replace('20261029/M04_verified','20261029/'+name).replace('138468',str(cells)).replace('AuditVerifiedM04.java','AuditFinal'+name+'.java')
final=final.replace('Files.createDirectories(out);','Files.createDirectories(out);\ns.getImportManager().importMeshFiles(List.of("'+meshfile.as_posix()+'"));')
final=final.replace('s.saveState(out.resolve("clean_import.sim").toString());','''for(star.base.report.Report rep:s.getReportManager().getObjects()){
 if(rep instanceof ForceReport){((ForceReport)rep).getParts().setObjects(fresh.getBoundaryManager().getBoundary("HF_012_wall"));((ForceReport)rep).setRepresentation(fv);}
 if(rep instanceof star.base.report.MaxReport && rep.getPresentationName().equals("Maximum Velocity")){((star.base.report.MaxReport)rep).getParts().setObjects(fresh);((star.base.report.MaxReport)rep).setRepresentation(fv);}
}
s.saveState(out.resolve("clean_import.sim").toString());''')
(R/('FinalizeSource'+name+'.java')).write_text(final)
audit=(R/'AuditQ2DM04.java').read_text().replace('AuditQ2DM04','AuditFinal'+name).replace('20261029/M04','20261029/'+name).replace('"M04"','"'+name+'"')
(R/('AuditFinal'+name+'.java')).write_text(audit)
jp=raw/'finalize_source_job.json'
b.write(jp,{'source':str(out/'input_raw_copy.sim'),'macro':str(R/('FinalizeSource'+name+'.java')),'log':str(raw/'finalize_source.log'),'np':2,'timeout_s':1800})
b.run([sys.executable,str(Q/'run_job.py'),str(jp)],raw/'finalize_source_runner.log',2100)
if b.read(raw/'finalize_source.exit.json',{}).get('returncode')!=0:raise RuntimeError('STAR import/audit failed')
b.run([b.PLOT,str(R/'audit_refinement_topology.py'),name],out/'topology_audit.log',600)
met=b.read(out/'measurement.json',{}).get('metrics',{});top=b.read(out/'topology_audit.json',{})
if any(met.get(k,1)!=0 for k in ['NegativeVolumeCells','UnclosedCells','DegeneratedFeCells']) or not top.get('single_layer_topology') or top.get('max_target_source_xz_displacement_m',1)>1e-12:raise RuntimeError('Final validity audit failed')
if met.get('min_cell_quality',0)<.01 or met.get('min_face_validity',0)<.5:raise RuntimeError('Low quality requires review')
shutil.copy2(meshfile.with_suffix('.validation.json'),out/'extrusion_validation.json')
b.write(out/'mesh_build.exit.json',{'returncode':0,'cells':cells,'exact_extrusion':True,'source_mesh':'M03','family_reference':'M04'})
b.write(raw/'build_status.json',{'status':'verified','cells':cells,'recovered_with_source_polygon_extrusion':True})
b.write(R/(name+'_ready.json'),{**c,'cells':cells,'status':'verified','source':str(out/'mesh.sim')})
print(json.dumps({'id':name,'status':'verified','cells':cells}),flush=True)
