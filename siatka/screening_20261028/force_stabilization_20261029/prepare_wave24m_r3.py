"""New R3: fresh six-face block avoids inherited surface assignment. No transient."""
from pathlib import Path
import json,shutil,hashlib,datetime
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');old=W/'W20_H24_X4_Q2D_r2';out=W/'W20_H24_X4_Q2D_r3'
assert not (W/'preparation.lock').exists()
out.mkdir(exist_ok=False)
src=Path('F:/ntnu/mesh_screening_20261028/inspection/baseline_clean.sim')
shutil.copy2(src,out/'baseline_copy.sim')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(src)==digest(out/'baseline_copy.sim')
job=json.loads((old/'job.json').read_text());job['id']=out.name;job['geometry_fix']='Fresh six-face no-foil block and explicit boundary assignments'
(out/'job.json').write_text(json.dumps(job,indent=2))
s=(old/'WaveTankBuild24m.java').read_text()
a='SimpleBlockPart domain=(SimpleBlockPart)s.getGeometryPartManager().getPart("DOMAIN");'
b='SimpleBlockPart domain=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());domain.setPresentationName("Wave24m_domain");'
assert s.count(a)==1;s=s.replace(a,b)
a='waveBox.setCorners(new DoubleVector(new double[]{xmin,y0,1.25}),new DoubleVector(new double[]{xmax,y1,2.75}));'
b=a+r'''
      domain.rebuildSimpleShapePart();waveBox.rebuildSimpleShapePart();
      PartSurface all=domain.getPartSurfaceManager().getPartSurfaces().iterator().next();
      domain.splitPartSurfaceByPatch(all,List.of(domain.getMinXFace()),"inlet",s);
      domain.splitPartSurfaceByPatch(all,List.of(domain.getMaxXFace()),"outlet",s);
      domain.splitPartSurfaceByPatch(all,List.of(domain.getMinYFace()),"span_source",s);
      domain.splitPartSurfaceByPatch(all,List.of(domain.getMaxYFace()),"span_target",s);
      domain.splitPartSurfaceByPatch(all,List.of(domain.getMinZFace()),"bottom",s);all.setPresentationName("top");
      Region mapRegion=s.getRegionManager().getRegion("fluid");mapRegion.getPartGroup().setObjects(domain);
      for(Boundary b:mapRegion.getBoundaryManager().getBoundaries())b.getPartSurfaceGroup().setObjects(new ArrayList<PartSurface>());
      for(PartSurface p:domain.getPartSurfaceManager().getPartSurfaces()){
        String key=p.getPresentationName();Boundary b;
        try{b=mapRegion.getBoundaryManager().getBoundary("DOMAIN."+key);}catch(Exception ex){b=mapRegion.getBoundaryManager().createEmptyBoundary();b.setPresentationName("DOMAIN."+key);}
        b.getPartSurfaceGroup().setObjects(p);
        if(key.equals("inlet"))b.setBoundaryType(InletBoundary.class);
        else if(key.equals("outlet")||key.equals("top"))b.setBoundaryType(PressureBoundary.class);
        else b.setBoundaryType(SymmetryBoundary.class);
      }
      List<Boundary> empty=new ArrayList<>();for(Boundary b:mapRegion.getBoundaryManager().getBoundaries())if(b.getPartSurfaceGroup().getObjects().isEmpty())empty.add(b);
      mapRegion.getBoundaryManager().removeObjects(empty);'''
assert s.count(a)==1;s=s.replace(a,b)
a='((VolumeCustomMeshControl)mesh.getCustomMeshControls().getObject("HF_fine")).setEnableControl(false);'
b=a+'\n      mesh.getInputGeometryObjects().setObjects(domain);'
s=s.replace(a,b)
s=s.replace('s.getMeshPipelineController().generateVolumeMesh();','mesh.execute();')
a='List<Object> gauges=new ArrayList<>();'
b=r'''List<Object> boundaries=new ArrayList<>();
      FieldFunction pos=s.getFieldFunctionManager().getFunction("Position");
      for(Boundary b:region.getBoundaryManager().getBoundaries()){
        AreaReport ar=s.getReportManager().createReport(AreaReport.class);ar.setRepresentation(fv);ar.getParts().setObjects(b);
        Map<String,Object> v=new LinkedHashMap<>();v.put("name",b.getPresentationName());v.put("area_m2",ar.getReportMonitorValue());v.put("type",b.getBoundaryType().getClass().getSimpleName());
        boundaries.add(v);
      }audit.put("boundaries",boundaries);
      UserFieldFunction calm=s.getFieldFunctionManager().createFieldFunction();calm.setFunctionName("AuditCalmAlpha");calm.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);calm.setDefinition("$$Position[2] < 2.0 ? 1.0 : 0.0");
      List<Object> gauges=new ArrayList<>();'''
s=s.replace(a,b)
a='Map<String,Object> g=new LinkedHashMap<>();g.put("x_m",x);'
b=a+r'''
        AreaReport area=s.getReportManager().createReport(AreaReport.class);area.setRepresentation(fv);area.getParts().setObjects(plane);
        g.put("plane_height_m",area.getReportMonitorValue()/(y1-y0));
        g.put("calm_eta_check_m",integral(fv,plane,calm)/(y1-y0)-h);'''
s=s.replace(a,b)
(out/'WaveTankBuild24m.java').write_text(s)
identity={'source':str(src),'source_sha256':digest(src),'copied_sha256':digest(out/'baseline_copy.sim'),'base_macro':str(old/'WaveTankBuild24m.java'),'macro_sha256':digest(out/'WaveTankBuild24m.java'),'created_at':datetime.datetime.now().astimezone().isoformat(),'status':'prepared','no_gpu':True,'workers':2}
(out/'source_identity.json').write_text(json.dumps(identity,indent=2))
runner=(R/'run_wave24m_preparation_r2.py').read_text().replace("W20_H24_X4_Q2D_r2","W20_H24_X4_Q2D_r3")
(R/'run_wave24m_preparation_r3.py').write_text(runner)
a=json.loads((old/'independent_geometry_audit.json').read_text())
failure={'status':'not_admitted_to_transient','case':old.name,'reason':'Independent CGNS has no inlet boundary, only four outlet faces, unintended wall/span topology. Rebuild fresh named six-face block; no transient steps were taken.','cells':a['cells'],'single_span':a['single_span'],'cells_touching_both_span_planes':a['cells_touching_both_span_planes'],'geometry_audit':str(old/'independent_geometry_audit.json'),'r2_preserved':True,'recovery_case':out.name}
(R/'wave_preparation_r2_review.json').write_text(json.dumps(failure,indent=2))
print(json.dumps({'prepared':str(out),'source_verified':True,'changes':'Fresh block, explicit six-face BC mapping, direct mesh input/execute, plane-area and calm-level diagnostic'}))
