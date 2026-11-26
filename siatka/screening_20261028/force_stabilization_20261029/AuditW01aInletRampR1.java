package macro;
import star.common.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.base.neo.*;import star.base.report.*;
import java.nio.file.*;import java.util.*;
/** Disposable CPU1 zero-flow audit only. Never initialize, clear, or step solution. */
public class AuditW01aInletRampR1 extends StarMacro {
 private Simulation s;private Region reg;private FvRepresentation fv;private Path out;
 private String js(Object o){if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(js(e.getKey().toString())+":"+js(e.getValue()));return j.toString();}if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Iterable<?>)o)j.add(js(x));return j.toString();}return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";}
 private void write(String n,Object x)throws Exception{Files.writeString(out.resolve(n),js(x));}
 private FieldFunction ff(String n){return s.getFieldFunctionManager().getFunction(n);}
 private FieldFunction waveField(VofWave w,String prefix){String name=prefix+w.getPresentationName();for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(name))return f;throw new IllegalStateException("Missing generated field "+name);}
 private VolumeIntegralReport volume(FieldFunction f){VolumeIntegralReport r=s.getReportManager().createReport(VolumeIntegralReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(reg);r.setSmooth(false);return r;}
 private MaxReport maximum(FieldFunction f,NamedObject p){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(p);return r;}
 private MinReport minimum(FieldFunction f){MinReport r=s.getReportManager().createReport(MinReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(reg);return r;}
 private ForceReport force(String name,double x,double z,ForceReportForceOption.Type type){ForceReport r=s.getReportManager().createReport(ForceReport.class);r.setPresentationName(name);r.setRepresentation(fv);r.getParts().setObjects(reg.getBoundaryManager().getBoundary("HF_012_wall"));r.getDirection().setComponents(x,0,z);r.getForceOption().setSelected(type);return r;}
 private Map<String,Object> physicalFingerprint(){
  Map<String,Object>d=new LinkedHashMap<>();d.put("time_s",s.getSolution().getPhysicalTime());d.put("cells",fv.getCellCount());
  d.put("mass_kg",volume(ff("Density")).getReportMonitorValue());d.put("water_volume_m3",volume(ff("VolumeFractionwater")).getReportMonitorValue());
  d.put("max_speed_m_s",maximum(ff("Velocity").getMagnitudeFunction(),reg).getReportMonitorValue());
  d.put("alpha_min",minimum(ff("VolumeFractionwater")).getReportMonitorValue());d.put("alpha_max",maximum(ff("VolumeFractionwater"),reg).getReportMonitorValue());
  d.put("Fx_N",force("Audit drag",1,0,ForceReportForceOption.Type.PRESSURE_AND_SHEAR).getReportMonitorValue());d.put("Fz_N",force("Audit lift",0,1,ForceReportForceOption.Type.PRESSURE_AND_SHEAR).getReportMonitorValue());
  d.put("pressure_drag_N",force("Audit pressure drag",1,0,ForceReportForceOption.Type.PRESSURE).getReportMonitorValue());d.put("viscous_drag_N",force("Audit viscous drag",1,0,ForceReportForceOption.Type.SHEAR).getReportMonitorValue());return d;
 }
 private void exportPhysical(String name,FieldFunction omega)throws Exception{
  XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(reg);tab.setRepresentation(fv);tab.setExtractVertexData(false);
  FieldFunction vel=ff("Velocity");ArrayList<FieldFunction> fields=new ArrayList<>(List.of(ff("VolumeFractionwater"),vel.getComponentFunction(0),vel.getComponentFunction(1),vel.getComponentFunction(2),vel.getMagnitudeFunction(),ff("Pressure"),ff("Density"),ff("CourantNumber")));
  if(omega!=null)fields.add(omega.getComponentFunction(1));tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(name).toString());s.getTableManager().removeObjects(tab);
 }
 private FifthOrderVofWave makeWave(VofWaveModel wm,String name){
  FifthOrderVofWave w=wm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,name);
  w.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);w.getVofWaveSpecification().getWaveLength().setValue(20);w.getWaterDepth().setValue(24);w.getWaveHeight().setValue(.5);
  w.getPointOnLevel().setComponents(0,0,2);w.getVerticalDirection().setComponents(0,0,1);w.getAdvancingDirection().setComponents(1,0,0);w.getCurrent().setComponents(18,0,0);w.getWind().setComponents(18,0,0);w.setFirstWaveFront(false);return w;
 }
 private SurfaceIntegralReport surface(FieldFunction f,NamedObject p){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(p);r.setSmooth(false);return r;}
 private Map<String,Object> analytical(FifthOrderVofWave w,List<PlaneSection> gauges,Boundary inlet){
  Map<String,Object>d=new LinkedHashMap<>();d.put("height_m",w.getWaveHeight().getValue());d.put("period_s",w.getWavePeriod().getValue());d.put("definition",w.getWaveHeight().getDefinition());d.put("first_front",w.getFirstWaveFront());
  FieldFunction a=waveField(w,"Volume Fraction of Heavy Fluid of "),v=waveField(w,"Velocity of ");
  ArrayList<Double> eta=new ArrayList<>();for(PlaneSection p:gauges)eta.add(surface(a,p).getReportMonitorValue()/.02-24);d.put("analytic_gauge_eta_m",eta);
  ArrayList<Double> meanV=new ArrayList<>();for(int i=0;i<3;i++)meanV.add(surface(v.getComponentFunction(i),inlet).getReportMonitorValue()/.6);d.put("analytic_inlet_mean_velocity_m_s",meanV);
  d.put("analytic_inlet_max_speed_m_s",maximum(v.getMagnitudeFunction(),inlet).getReportMonitorValue());return d;
 }
 private double maxListDiff(Object a,Object b){List<?> x=(List<?>)a,y=(List<?>)b;double m=0;for(int i=0;i<x.size();i++){double v=((Number)x.get(i)).doubleValue(),w=((Number)y.get(i)).doubleValue();if(!Double.isFinite(v)||!Double.isFinite(w))return Double.NaN;m=Math.max(m,Math.abs(v-w));}return m;}
 private String rampExpression(double origin,double duration){
  String tau="min(1.0,max(0.0,($Time-<"+origin+" s>)/<"+duration+" s>))";
  return "<0.000001 m>+<0.499999 m>*0.5*(1.0-cos(3.141592653589793*"+tau+"))";
 }
 private void view(String name,PlaneSection plane,FieldFunction f,double xc,double zc,double scale){
  Scene sc=s.getSceneManager().createScene(name);ScalarDisplayer d=sc.getDisplayerManager().createScalarDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(plane);d.getScalarDisplayQuantity().setFieldFunction(f);d.getScalarDisplayQuantity().setAutoRange(true);
  PartDisplayer foil=sc.getDisplayerManager().createPartDisplayer("Computed foil outline");foil.setRepresentation(fv);foil.getInputParts().setObjects(reg.getBoundaryManager().getBoundary("HF_012_wall"));foil.setSurface(true);foil.setOutline(true);
  CurrentView cv=sc.getCurrentView();cv.setProjectionMode(VisProjectionMode.PARALLEL);cv.setFocalPoint(new DoubleVector(new double[]{xc,.02,zc}));cv.setPosition(new DoubleVector(new double[]{xc,-100,zc}));cv.setViewUp(new DoubleVector(new double[]{0,0,1}));cv.setParallelScale(scale);
 }
 public void execute(){
  s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_W01A_RAMP_AUDIT_OUT")));
  try{
   if(s.getNumberOfGpgpus()!=0||Math.abs(s.getSolution().getPhysicalTime()-.02)>1e-10)throw new IllegalStateException("Requires CPU/noGPU computed calm t.020 checkpoint");
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable copy required");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");if(fv.getCellCount()!=317277)throw new IllegalStateException("Source mesh count differs");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   Map<String,Object> before=physicalFingerprint();write("physical_before.json",before);
   FieldFunction omega=null;for(Object obj:s.getFieldFunctionManager().getVectorFieldFunctions())if(obj instanceof VorticityVectorFunction){if(omega!=null)throw new IllegalStateException("Ambiguous native vorticity");omega=(FieldFunction)obj;}
   Map<String,Object> vort=new LinkedHashMap<>();vort.put("lookup","instanceof star.flow.VorticityVectorFunction in getVectorFieldFunctions");vort.put("found",omega!=null);
   if(omega!=null){vort.put("function_name",omega.getFunctionName());vort.put("presentation_name",omega.getPresentationName());vort.put("class",omega.getClass().getName());vort.put("component_index",1);vort.put("component_meaning","omega_y = du/dz - dw/dx for x-z flow");vort.put("omega_y_min_per_s",minimum(omega.getComponentFunction(1)).getReportMonitorValue());vort.put("omega_y_max_per_s",maximum(omega.getComponentFunction(1),reg).getReportMonitorValue());}
   write("native_vorticity_lookup.json",vort);exportPhysical("physical_fields_before.csv",omega);
   PhysicsContinuum pc=reg.getPhysicsContinuum();VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);wm.setEnableTheoryComparison(true);
   FifthOrderVofWave expressionWave=makeWave(wm,"W01a_Ramp_Expression_Audit"),constantWave=makeWave(wm,"W01a_Ramp_Constant_Audit");
   Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
   ArrayList<PlaneSection> gauges=new ArrayList<>();ArrayList<Double> locations=new ArrayList<>();
   for(double x:new double[]{-34.99,-25,-15,-10,-5,0,5,10}){PlaneSection p=s.getPartManager().createPlaneSection();p.setPresentationName("Audit analytic plane x"+x);p.getInputParts().setObjects(reg);p.setOrigin(new DoubleVector(new double[]{x,.02,0}));p.setOrientation(new DoubleVector(new double[]{1,0,0}));gauges.add(p);locations.add(x);}
   double time=s.getSolution().getPhysicalTime(),duration=2*.8472673206891129;ArrayList<Object> tests=new ArrayList<>();boolean rampPass=true;
   for(double tau:new double[]{0,.5,1}){
    Map<String,Object> row=new LinkedHashMap<>();double origin=time-tau*duration,expected=.000001+.499999*.5*(1-Math.cos(Math.PI*tau));row.put("tau",tau);row.put("fixed_physical_time_s",time);row.put("test_origin_s",origin);row.put("expected_height_m",expected);
    try{
     expressionWave.getWaveHeight().setDefinition(rampExpression(origin,duration));constantWave.getWaveHeight().setValue(expected);
     Map<String,Object> exp=analytical(expressionWave,gauges,inlet),con=analytical(constantWave,gauges,inlet);
     double ed=maxListDiff(exp.get("analytic_gauge_eta_m"),con.get("analytic_gauge_eta_m")),vd=maxListDiff(exp.get("analytic_inlet_mean_velocity_m_s"),con.get("analytic_inlet_mean_velocity_m_s"));
     double ep=((Number)exp.get("period_s")).doubleValue(),cp=((Number)con.get("period_s")).doubleValue(),hv=((Number)exp.get("height_m")).doubleValue();
     boolean pass=Double.isFinite(hv)&&Math.abs(hv-expected)<1e-9&&Double.isFinite(ep)&&Double.isFinite(cp)&&ep>0&&Math.abs(ep-cp)<1e-9&&Double.isFinite(ed)&&ed<1e-8&&Double.isFinite(vd)&&vd<1e-8;
     row.put("expression",exp);row.put("constant",con);row.put("max_gauge_difference_m",ed);row.put("max_mean_velocity_difference_m_s",vd);row.put("pass",pass);rampPass&=pass;
    }catch(Exception e){row.put("pass",false);row.put("error",e.toString());rampPass=false;}
    tests.add(row);write("ramp_tests_partial.json",tests);
   }
   // An explicit setter-only cache test is separate from the time-expression tests.
   ArrayList<Object> setterTests=new ArrayList<>();
   for(double h:new double[]{.000001,.2500005,.5}){
    Map<String,Object> row=new LinkedHashMap<>();row.put("requested_height_m",h);
    try{expressionWave.getWaveHeight().setValue(h);row.put("sample",analytical(expressionWave,gauges,inlet));row.put("evaluated",true);}
    catch(Exception e){row.put("evaluated",false);row.put("error",e.toString());}
    setterTests.add(row);
   }
   // Restore a ramp beginning now; bind boundaries/forcing only, never initial conditions.
   expressionWave.getWaveHeight().setDefinition(rampExpression(time,duration));
   inlet.getValues().get(VelocityProfile.class).setMethod(FunctionVectorProfileMethod.class);
   inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveField(expressionWave,"Velocity of "));
   VolumeFractionProfile vp=inlet.getValues().get(VolumeFractionProfile.class);vp.setMethod(CompositeNMinus1ArrayProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveField(expressionWave,"Volume Fraction of Heavy Fluid of "));
   reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(expressionWave);
   Map<String,Object> binding=new LinkedHashMap<>();binding.put("scope","Only inlet velocity/phase and existing inlet forcing target changed in this disposable audit. Computed fields and continuum initial-condition profiles retained.");binding.put("forcing_wave",reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave().getPresentationName());binding.put("first_front",expressionWave.getFirstWaveFront());binding.put("wave_height_definition",expressionWave.getWaveHeight().getDefinition());
   ArrayList<Object> boundaries=new ArrayList<>();for(Boundary b:reg.getBoundaryManager().getBoundaries()){Map<String,Object> br=new LinkedHashMap<>();br.put("name",b.getPresentationName());br.put("forcing",String.valueOf(b.getConditions().get(VofWaveForcingBoundaryOption.class).getSelectedElement()));br.put("damping",String.valueOf(b.getConditions().get(VofWaveDampingBoundaryOption.class).getSelectedElement()));boundaries.add(br);}binding.put("boundaries",boundaries);write("binding_audit.json",binding);
   Map<String,Object> after=physicalFingerprint();write("physical_after.json",after);boolean unchanged=true;Map<String,Object> delta=new LinkedHashMap<>();
   for(String k:before.keySet()){double a=((Number)before.get(k)).doubleValue(),b=((Number)after.get(k)).doubleValue();delta.put(k,b-a);if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a-b)>1e-10*Math.max(1,Math.abs(a)))unchanged=false;}
   exportPhysical("physical_fields.csv",omega);
   PlaneSection mid=s.getPartManager().createPlaneSection();mid.setPresentationName("Actual computed calm t0.020 midspan");mid.getInputParts().setObjects(reg);mid.setOrigin(new DoubleVector(new double[]{0,.02,0}));mid.setOrientation(new DoubleVector(new double[]{0,1,0}));
   view("W01a actual calm t0.020 - water fraction",mid,ff("VolumeFractionwater"),5,2,23);
   view("W01a actual calm t0.020 - pressure",mid,ff("Pressure"),.6,0,1.5);
   if(omega!=null){view("W01a actual calm t0.020 - signed omega_y",mid,omega.getComponentFunction(1),.6,0,1.5);view("W01a actual calm t0.020 - core signed omega_y",mid,omega.getComponentFunction(1),0,1,6);}
   s.saveState(out.resolve("inspection.sim").toString());
   Map<String,Object> result=new LinkedHashMap<>();result.put("status",unchanged?"zero_step_audit_complete":"physical_fingerprint_mismatch");result.put("physical_fields_fingerprint_unchanged",unchanged);result.put("physical_deltas",delta);result.put("time_s",s.getSolution().getPhysicalTime());result.put("cells",fv.getCellCount());result.put("flow_steps",0);result.put("initialized_or_cleared",false);result.put("gpu_count",s.getNumberOfGpgpus());result.put("ramp_expression_tests_pass",rampPass);result.put("ramp_tests",tests);result.put("setter_cache_tests",setterTests);result.put("analytic_gauge_x_m",locations);result.put("native_vorticity",vort);result.put("note","Actual physical fields are the computed calm checkpoint. Analytical FifthOrder reference tests do not propagate a wave and do not validate transient refresh between CFD steps. Tiny minimum H=1e-6 m avoids testing the H=0 singular limit. inspection.sim is diagnostic only, not production admission.");
   write("audit.json",result);if(!unchanged)throw new IllegalStateException("Physical fields changed without stepping");
  }catch(Exception e){try{write("audit_error.json",Map.of("error",e.toString(),"time_s",s.getSolution().getPhysicalTime(),"flow_steps",0));}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
