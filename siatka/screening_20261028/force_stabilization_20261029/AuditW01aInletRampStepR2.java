package macro;
import star.common.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.base.neo.*;import star.base.report.*;
import java.nio.file.*;import java.util.*;
/** Disposable CPU1 bounded three-step runtime cache audit. Never initialize or clear solution. */
public class AuditW01aInletRampStepR2 extends StarMacro {
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

 private boolean finite(Object x){if(x instanceof Number)return Double.isFinite(((Number)x).doubleValue());if(x instanceof Map){for(Object v:((Map<?,?>)x).values())if(!finite(v))return false;}if(x instanceof List){for(Object v:(List<?>)x)if(!finite(v))return false;}return x!=null;}
 public void execute(){
  s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_W01A_RAMP_AUDIT_OUT")));int done=0;
  try{
   double origin=s.getSolution().getPhysicalTime(),dt=.001,duration=2*.8472673206891129;
   if(s.getNumberOfGpgpus()!=0||Math.abs(origin-.587)>1e-10)throw new IllegalStateException("Requires CPU/noGPU computed calm t.587 final");
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable copy required");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");if(fv.getCellCount()!=317277)throw new IllegalStateException("Mesh differs");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   Map<String,Object> before=physicalFingerprint();write("physical_before.json",before);
   FieldFunction omega=null;for(Object o:s.getFieldFunctionManager().getVectorFieldFunctions())if(o instanceof VorticityVectorFunction)omega=(FieldFunction)o;
   if(omega==null)throw new IllegalStateException("Native vorticity missing");
   write("native_vorticity_lookup.json",Map.of("function_name",omega.getFunctionName(),"class",omega.getClass().getName(),"component_index",1));
   PhysicsContinuum pc=reg.getPhysicsContinuum();VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);wm.setEnableTheoryComparison(true);
   FifthOrderVofWave expressionWave=makeWave(wm,"W01a_Ramp_Runtime_Audit"),constantWave=makeWave(wm,"W01a_Constant_Runtime_Audit");
   expressionWave.getWaveHeight().setDefinition(rampExpression(origin,duration));constantWave.getWaveHeight().setValue(.000001);
   Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
   inlet.getValues().get(VelocityProfile.class).setMethod(FunctionVectorProfileMethod.class);
   inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveField(expressionWave,"Velocity of "));
   VolumeFractionProfile vp=inlet.getValues().get(VolumeFractionProfile.class);vp.setMethod(CompositeNMinus1ArrayProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveField(expressionWave,"Volume Fraction of Heavy Fluid of "));
   reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(expressionWave);
   ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-dt)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("Requires existing SO1ms");
   for(Object x:s.getSolverStoppingCriterionManager().getChildren()){if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);((SolverStoppingCriterion)x).setIsUsed(true);}}
   ArrayList<PlaneSection> gauges=new ArrayList<>();for(double x:new double[]{-34.99,-25,-15,-10,-5,0,5,10}){PlaneSection p=s.getPartManager().createPlaneSection();p.setPresentationName("Runtime audit gauge x"+x);p.getInputParts().setObjects(reg);p.setOrigin(new DoubleVector(new double[]{x,.02,0}));p.setOrientation(new DoubleVector(new double[]{1,0,0}));gauges.add(p);}
   Map<String,Object> configured=physicalFingerprint();boolean unchanged=true;for(String k:before.keySet()){double a=((Number)before.get(k)).doubleValue(),b=((Number)configured.get(k)).doubleValue();if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a-b)>1e-10*Math.max(1,Math.abs(a)))unchanged=false;}
   write("configuration_fingerprint.json",Map.of("before",before,"after",configured,"unchanged",unchanged));if(!unchanged)throw new IllegalStateException("Configuration changed physical fields");
   ArrayList<Object> rows=new ArrayList<>();
   for(int i=1;i<=3;i++){
    if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL")))throw new IllegalStateException("Stop marker");
    double expected=.000001+.499999*.5*(1-Math.cos(Math.PI*(i*dt)/duration));constantWave.getWaveHeight().setValue(expected);
    s.getSimulationIterator().step(1);done=i;double t=s.getSolution().getPhysicalTime();
    Map<String,Object> phys=physicalFingerprint(),exp=analytical(expressionWave,gauges,inlet),con=analytical(constantWave,gauges,inlet),row=new LinkedHashMap<>();
    double ed=maxListDiff(exp.get("analytic_gauge_eta_m"),con.get("analytic_gauge_eta_m")),vd=maxListDiff(exp.get("analytic_inlet_mean_velocity_m_s"),con.get("analytic_inlet_mean_velocity_m_s"));
    double period=((Number)exp.get("period_s")).doubleValue();boolean pp=finite(phys)&&((Number)phys.get("max_speed_m_s")).doubleValue()<50&&((Number)phys.get("alpha_min")).doubleValue()>=-1e-8&&((Number)phys.get("alpha_max")).doubleValue()<=1+1e-8&&Math.abs(t-origin-i*dt)<1e-10;
    boolean ap=finite(exp)&&period>0&&Math.abs(((Number)exp.get("height_m")).doubleValue()-expected)<1e-10;
    row.put("step",i);row.put("time_s",t);row.put("expected_height_m",expected);row.put("physical",phys);row.put("expression",exp);row.put("constant",con);row.put("max_gauge_difference_m",ed);row.put("max_mean_velocity_difference_m_s",vd);row.put("physical_guard_pass",pp);row.put("analytic_finite_pass",ap);
    row.put("native_water_error_kg_step",s.getReportManager().getReport("Inspect_NativeWater_MassConservationError").getReportMonitorValue());row.put("native_air_error_kg_step",s.getReportManager().getReport("Inspect_NativeAir_MassConservationError").getReportMonitorValue());
    rows.add(row);write("guarded_step_results.json",rows);
    if(!pp||!ap)throw new IllegalStateException("First/runtime guarded step failed physical="+pp+" analytic="+ap);
   }
   exportPhysical("physical_fields.csv",omega);s.saveState(out.resolve("final.sim").toString());
   write("audit.json",Map.of("status","three_guarded_steps_completed","flow_steps",done,"time_s",s.getSolution().getPhysicalTime(),"source_time_s",origin,"configuration_fingerprint_unchanged",unchanged,"initialized_or_cleared",false,"gpu_count",0,"guarded_steps",rows,"note","Three near-zero-height runtime steps test immediate cache readiness only. They do not validate full-height nonlinear ramp refresh or wave-force accuracy."));
  }catch(Exception e){try{write("audit_error.json",Map.of("error",e.toString(),"time_s",s.getSolution().getPhysicalTime(),"flow_steps",done));s.saveState(out.resolve("error_preserved.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
