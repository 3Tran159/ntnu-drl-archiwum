from pathlib import Path
import hashlib,json,shutil,datetime
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');old=W/'W20_H24_X4_Q2D_r3';out=W/'W20_H24_X4_Q2D_r4'
assert not (W/'preparation.lock').exists()
out.mkdir(exist_ok=False);src=Path('F:/ntnu/mesh_screening_20261028/inspection/baseline_clean.sim');shutil.copy2(src,out/'baseline_copy.sim')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)==sha(out/'baseline_copy.sim')
j=json.loads((old/'job.json').read_text());j['id']=out.name;(out/'job.json').write_text(json.dumps(j,indent=2))
s=(old/'WaveTankBuild24m.java').read_text()
s=s.replace('List<Object> boundaries=new ArrayList<>();','UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setFunctionName("AuditUnit");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDefinition("1.0");\n      List<Object> boundaries=new ArrayList<>();')
s=s.replace('AreaReport ar=s.getReportManager().createReport(AreaReport.class);ar.setRepresentation(fv);','SurfaceIntegralReport ar=s.getReportManager().createReport(SurfaceIntegralReport.class);ar.setFieldFunction(one);ar.setRepresentation(fv);')
s=s.replace('AreaReport area=s.getReportManager().createReport(AreaReport.class);area.setRepresentation(fv);','SurfaceIntegralReport area=s.getReportManager().createReport(SurfaceIntegralReport.class);area.setFieldFunction(one);area.setRepresentation(fv);')
s=s.replace('q.setRepresentation(fv);return q.getReportMonitorValue();','q.setRepresentation(fv);q.setSmooth(false);return q.getReportMonitorValue();')
(out/'WaveTankBuild24m.java').write_text(s)
i={'source':str(src),'source_sha256':sha(src),'copied_sha256':sha(out/'baseline_copy.sim'),'base_macro':str(old/'WaveTankBuild24m.java'),'macro_sha256':sha(out/'WaveTankBuild24m.java'),'created_at':datetime.datetime.now().astimezone().isoformat(),'status':'prepared','no_gpu':True,'workers':2}
(out/'source_identity.json').write_text(json.dumps(i,indent=2))
(R/'run_wave24m_preparation_r4.py').write_text((R/'run_wave24m_preparation_r3.py').read_text().replace('W20_H24_X4_Q2D_r3','W20_H24_X4_Q2D_r4'))
(R/'wave_preparation_r3_failure.json').write_text(json.dumps({'status':'compile_failure_preserved','reason':'AreaReport class unavailable. R4 uses verified SurfaceIntegralReport with unit scalar; geometry plan unchanged.','recovery':out.name},indent=2))
# This pilot macro has never been run; fix its same area-report dependency before copying into any attempt.
p=R/'WavePropagationCheck.java';s=p.read_text();s=s.replace('double[] xs={','UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setFunctionName("PropagationUnit");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDefinition("1.0");\n   double[] xs={')
s=s.replace('AreaReport ar=s.getReportManager().createReport(AreaReport.class);ar.setRepresentation(fv);','SurfaceIntegralReport ar=s.getReportManager().createReport(SurfaceIntegralReport.class);ar.setFieldFunction(one);ar.setRepresentation(fv);')
p.write_text(s)
print(json.dumps({'prepared':str(out),'source_verified':True}))
