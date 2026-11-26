from pathlib import Path
import json,hashlib,shutil,datetime
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');old=W/'W20_H24_X4_Q2D_r4';out=W/'W20_H24_X4_Q2D_r5'
assert not (W/'preparation.lock').exists() and (out/'mesh_exact.validation.json').exists() and not (out/'job.json').exists()
src=Path('F:/ntnu/mesh_screening_20261028/inspection/baseline_clean.sim');shutil.copy2(src,out/'baseline_copy.sim')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)==sha(out/'baseline_copy.sim')
j=json.loads((old/'job.json').read_text());j['id']=out.name;j['geometry_fix']='Import independently constructed exact Cartesian no-foil mesh';(out/'job.json').write_text(json.dumps(j,indent=2))
s=(old/'WaveTankBuild24m.java').read_text()
a='PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");'
b=r'''s.getImportManager().importMeshFiles(List.of(out.resolve("mesh_exact.CGNS").toString()));
      Region oldRegion=s.getRegionManager().getRegion("fluid"),fresh=s.getRegionManager().getRegion("fluid 2");
      fresh.setPhysicsContinuum(oldRegion.getPhysicsContinuum());
      for(Boundary b:oldRegion.getBoundaryManager().getBoundaries()){
        Boundary n=fresh.getBoundaryManager().getBoundary(b.getPresentationName());String name=n.getPresentationName();n.copyProperties(b);n.setPresentationName(name);
        if(!n.getBoundaryType().getClass().equals(b.getBoundaryType().getClass()))throw new IllegalStateException("Boundary type transfer failed");
      }
      s.getRegionManager().removeObjects(List.of(oldRegion));fresh.setPresentationName("fluid");
      '''+a
assert s.count(a)==1;s=s.replace(a,b).replace('mesh.execute();','// Mesh imported from independently verified Cartesian CGNS; do not remesh.')
a='v.put("area_m2",ar.getReportMonitorValue());'
b=a+r'''double expectedArea=b.getPresentationName().contains("span_")?2400:(b.getPresentationName().endsWith("inlet")||b.getPresentationName().endsWith("outlet"))?.6:1.6;
        if(!Double.isFinite(ar.getReportMonitorValue())||Math.abs(ar.getReportMonitorValue()-expectedArea)>expectedArea*1e-7)throw new IllegalStateException("Boundary area mismatch: "+b.getPresentationName());'''
assert s.count(a)==1;s=s.replace(a,b)
a='g.put("plane_height_m",area.getReportMonitorValue()/(y1-y0));'
b=a+r'''if(Math.abs(area.getReportMonitorValue()/(y1-y0)-30)>1e-5)throw new IllegalStateException("Incomplete gauge plane");'''
s=s.replace(a,b)
(out/'WaveTankBuild24m.java').write_text(s)
i={'source':str(src),'source_sha256':sha(src),'copied_sha256':sha(out/'baseline_copy.sim'),'macro_sha256':sha(out/'WaveTankBuild24m.java'),'mesh_sha256':sha(out/'mesh_exact.CGNS'),'created_at':datetime.datetime.now().astimezone().isoformat(),'status':'prepared','no_gpu':True,'workers':2}
(out/'source_identity.json').write_text(json.dumps(i,indent=2))
(R/'run_wave24m_preparation_r5.py').write_text((R/'run_wave24m_preparation_r4.py').read_text().replace('W20_H24_X4_Q2D_r4','W20_H24_X4_Q2D_r5'))
(R/'wave_preparation_r4_review.json').write_text(json.dumps({'status':'not_admitted_to_transient','reason':'Fresh boundary assignment did not repair native thin-slab trimming. Gauge height29.0181m instead30m; calm reference -0.48916m; inlet/top/bottom reports nonfinite. R5 uses exact Cartesian CGNS, no remeshing.','source_preserved':True,'recovery':out.name},indent=2))
# Not yet run; use the exact mesh attempt as pilot source.
p=R/'run_wave24m_propagation_r1.py';p.write_text(p.read_text().replace("srcdir=W/'W20_H24_X4_Q2D_r4'","srcdir=W/'W20_H24_X4_Q2D_r5'"))
print(json.dumps({'prepared':out.name,'cells':json.loads((out/'mesh_exact.validation.json').read_text())['cells']}))
