"""Prepare a new24m no-foil CPU mesh/audit; no solver launch in this script."""
from pathlib import Path
import json,hashlib,shutil,datetime
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');out=W/'W20_H24_X4_Q2D_r1'
out.mkdir(exist_ok=False)
src=Path('F:/ntnu/mesh_screening_20261028/inspection/baseline_clean.sim');copy=out/'baseline_copy.sim';shutil.copy2(src,copy)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(src)==digest(copy)
job={'id':out.name,'lambda_m':20,'depth_m':24,'height_m':.5,'dt_s':.001,'domain_lambda':4,'mesh':True,'scope':'No-foil24m propagation preparation only; no production force result','wave_model':'FifthOrderVofWave','span_m':.02,'top_z_m':8,'first_wave_front':False}
(out/'job.json').write_text(json.dumps(job,indent=2))
base=Path('F:/ntnu/wave_depth_20261029/WaveTankBuildFifth.java')
s=base.read_text();s=s.replace('public class WaveTankBuildFifth','public class WaveTankBuild24m')
s=s.replace('import star.flow.*;','import star.flow.*;\nimport star.vis.*;\nimport star.post.*;\nimport java.lang.reflect.*;')
s=s.replace('double y0=20.0,y1=20.8,wl=2.0,bottom=wl-h,top=12.0;','double y0=20.0,y1=20.02,wl=2.0,bottom=wl-h,top=8.0;')
s=s.replace('wm.setEnableTheoryComparison(false);','wave.getClass().getMethod("setFirstWaveFront",boolean.class).invoke(wave,false);\n      if(!Boolean.FALSE.equals(wave.getClass().getMethod("getFirstWaveFront").invoke(wave)))throw new IllegalStateException("First-wave-front setting not applied");\n      wm.setEnableTheoryComparison(true);')
s=s.replace('s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(dt);','s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeDiscretization().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);\n      s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(dt);')
old='s.println("[NTNU_FIFTH] START INITIALIZATION");s.getSolution().initializeSolution();s.println("[NTNU_FIFTH] INITIALIZED");s.saveState(out.resolve("built.sim").toString());'
new=r'''s.println("[NTNU_FIFTH] START INITIALIZATION");s.getSolution().initializeSolution();s.println("[NTNU_FIFTH] INITIALIZED");
      FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
      FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
      Map<String,Object> audit=new LinkedHashMap<>();
      audit.put("time_s",s.getSolution().getPhysicalTime());audit.put("steps_taken",0);audit.put("cells",fv.getCellCount());
      audit.put("depth_m",h);audit.put("top_z_m",top);audit.put("span_m",y1-y0);audit.put("waterline_z_m",wl);
      audit.put("wave_class",wave.getClass().getName());audit.put("first_wave_front",wave.getClass().getMethod("getFirstWaveFront").invoke(wave));
      audit.put("wave_name",wave.getPresentationName());audit.put("wave_period_s",wave.getWavePeriod().getValue());
      audit.put("advancing_direction",wave.getAdvancingDirection().toString());audit.put("current",wave.getCurrent().toString());
      Map<String,Object> bindings=new LinkedHashMap<>();
      bindings.put("initial_velocity",pc.getInitialConditions().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction().getFunctionName());
      bindings.put("inlet_velocity",inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction().getFunctionName());
      bindings.put("initial_alpha",pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction().getFunctionName());
      bindings.put("inlet_alpha",inlet.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction().getFunctionName());
      bindings.put("outlet_pressure",outlet.getValues().get(StaticPressureProfile.class).getMethod(FunctionScalarProfileMethod.class).getFieldFunction().getFunctionName());
      bindings.put("forcing_wave",region.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave().getPresentationName());
      audit.put("profile_bindings",bindings);
      List<Object> gauges=new ArrayList<>();
      for(double x:new double[]{-lambda/2,0,lambda/8,lambda/4,lambda/2}){
        PlaneSection plane=s.getPartManager().createPlaneSection();plane.setPresentationName("InitGauge_"+x);plane.getInputParts().setObjects(region);
        plane.setOrigin(new DoubleVector(new double[]{x,(y0+y1)/2,wl}));plane.setOrientation(new DoubleVector(new double[]{1,0,0}));
        Map<String,Object> g=new LinkedHashMap<>();g.put("x_m",x);
        g.put("eta_actual_m",integral(fv,plane,alpha)/(y1-y0)-h);g.put("eta_analytic_m",integral(fv,plane,frac)/(y1-y0)-h);gauges.add(g);
      }audit.put("initial_gauges",gauges);
      for(String name:new String[]{"CellQuality","FaceValidity","VolumeFractionwater"}){
        MinReport min=s.getReportManager().createReport(MinReport.class);min.setFieldFunction(s.getFieldFunctionManager().getFunction(name));min.setRepresentation(fv);min.getParts().setObjects(region);audit.put("min_"+name,min.getReportMonitorValue());
        if(name.equals("VolumeFractionwater")){MaxReport max=s.getReportManager().createReport(MaxReport.class);max.setFieldFunction(alpha);max.setRepresentation(fv);max.getParts().setObjects(region);audit.put("max_alpha",max.getReportMonitorValue());}
      }
      ImportManager im=s.getImportManager();im.setFormatType(SolutionExportFormat.Type.CGNS);
      im.export(out.resolve("mesh.CGNS").toString(),List.of(region),List.of(s.getFieldFunctionManager().getFunction("CellQuality"),alpha),List.of());
      Files.writeString(out.resolve("initial_audit.json"),json(audit));
      s.saveState(out.resolve("built.sim").toString());'''
assert s.count(old)==1;s=s.replace(old,new)
helper=r'''
  private double integral(FvRepresentation fv,PlaneSection p,FieldFunction f){
    SurfaceIntegralReport q=s.getReportManager().createReport(SurfaceIntegralReport.class);q.setFieldFunction(f);q.getParts().setObjects(p);q.setRepresentation(fv);return q.getReportMonitorValue();
  }
  private String json(Object o){
    if(o==null)return "null";if(o instanceof Number||o instanceof Boolean)return o.toString();
    if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Map.Entry<?,?> e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
    if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Iterable<?>)o)j.add(json(a));return j.toString();}
    return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
  }
'''
s=s.rstrip()[:-1]+helper+'\n}\n'
(out/'WaveTankBuild24m.java').write_text(s)
identity={'source':str(src),'source_sha256':digest(src),'copied_sha256':digest(copy),'base_macro':str(base),'base_macro_sha256':digest(base),'macro_sha256':digest(out/'WaveTankBuild24m.java'),'created_at':datetime.datetime.now().astimezone().isoformat(),'status':'prepared','no_gpu':True,'workers':2}
(out/'source_identity.json').write_text(json.dumps(identity,indent=2))
(R/'wave_preparation_state.json').write_text(json.dumps({'status':'prepared_24m_cpu_build','case':job['id'],'directory':str(out),'workers':2,'gpu':False,'scope':'Meshing and zero-step profile/initial-wave audit only'},indent=2))
print(json.dumps({'directory':str(out),'status':'prepared','source_copy_verified':True}))
