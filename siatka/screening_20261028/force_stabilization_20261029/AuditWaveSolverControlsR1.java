package macro;
import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.flow.*;
import star.vof.*;
import java.nio.file.*;
import java.util.*;
import java.lang.reflect.*;
public class AuditWaveSolverControlsR1 extends StarMacro {
 private Simulation s; private FvRepresentation fv; private Path out;
 private static String json(Object o){
  if(o==null)return "null";
  if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";
  if(o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
  if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Collection<?>)o)j.add(json(a));return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
 private static Object inspect(Object o,int depth){
  if(o==null||o instanceof String||o instanceof Number||o instanceof Boolean||o instanceof Enum)return o;
  if(depth<=0)return o.toString();
  if(o instanceof Collection){List<Object>a=new ArrayList<>();for(Object x:(Collection<?>)o)a.add(inspect(x,depth-1));return a;}
  Map<String,Object>d=new LinkedHashMap<>();d.put("class",o.getClass().getName());
  String allowed="getPresentationName|getSelected|getSelectedElement|getMethod|getFieldFunction|getFunctionName|getConstant|getQuantity|getValue|getSIValue|getSIVector|getDefinition|getObjects|getProfiles|getTimeDiscretizationOption|getTimeStep|getFreezeTime|getSubStepCount|getFixedSubStepCount|getSubStepSpecification|getMaxDynamicSubStepCount|getTargetCfl|getCutOffPercentage|getUrf|getFaceDensityReconOption|getVolumeFractionUpwindOption|getMixtureDensityGradient|getHRICSchemeParameters|getMHRICSchemeParameters|getSharpeningFactor|getAngleFactor|getCFL_l|getCFL_u|getForcingVofWave|getPhaseManager|getMaterialProperties|getAMGLinearSolver|getConvergeTol|getMaxCycles|getEpsilon|getVerbosityEnum|getTotalNumberCycles|getTotalSolveElapsedTime|getSelectedCycleOption|getSelectedSmootherOption|getPressureSolver|getVelocitySolver|getSchemeOption|getScheme|getFreezeFlow|getReconFreeze|getReconZero|getBadCellRobustnessTreatment|getLeaveTemporaryStorage|getUrfQuantity|getNumNonOrthogonalCorrectors|getPisoAMGOptions|getUseDynamicLocalUrf";
  for(Method m:o.getClass().getMethods())if(m.getParameterCount()==0&&m.getName().matches(allowed)){
   try{d.put(m.getName(),inspect(m.invoke(o),depth-1));}catch(Exception e){d.put(m.getName(),"READ_ERROR:"+e.getClass().getSimpleName());}
  }
  return d;
 }
 private static Object getter(Object o,String method){
  try{return inspect(o.getClass().getMethod(method).invoke(o),3);}catch(Exception e){return "UNAVAILABLE:"+e.getClass().getSimpleName();}
 }
 private Map<String,Object> definition(AnalysisReport r){
  Map<String,Object>d=new LinkedHashMap<>();d.put("name",r.getPresentationName());d.put("class",r.getClass().getName());d.put("smooth",r.getSmooth());
  d.put("idealization",getter(r,"getUseIdealization"));d.put("representation",inspect(r.getRepresentation(),2));d.put("parts",inspect(r.getParts().getObjects(),2));
  if(r instanceof ScalarReport){ScalarReport q=(ScalarReport)r;d.put("field_function",inspect(q.getFieldFunction(),2));d.put("value",q.getReportMonitorValue());}
  d.put("error_log",r.getErrorLog());return d;
 }
 private Map<String,Object> unsmoothed(AnalysisReport r){
  r.setRepresentation(fv);r.setSmooth(false);
  try{r.getClass().getMethod("setUseIdealization",boolean.class).invoke(r,false);}catch(NoSuchMethodException e){}catch(Exception e){throw new RuntimeException(e);}
  return definition(r);
 }
 public void execute(){
  s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_REPORT_AUDIT_OUT")));
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable copy required");
   if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only zero-step audit required");
   double before=s.getSolution().getPhysicalTime();
   if(Math.abs(before-.75)>1e-8)throw new IllegalStateException("Expected preserved R4 t0.750 checkpoint");
   fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()!=53200)throw new IllegalStateException("Unexpected mesh");
   Region reg=s.getRegionManager().getRegion("fluid");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   List<Report> saved=new ArrayList<>(s.getReportManager().getObjects());
   List<Object> oldReports=new ArrayList<>();
   for(Report r:saved)if(r instanceof MassFlowReport||r instanceof VolumeIntegralReport)oldReports.add(definition((AnalysisReport)r));
   Files.writeString(out.resolve("existing_report_definitions.json"),json(oldReports));
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   List<Object> models=new ArrayList<>(),solvers=new ArrayList<>(),sources=new ArrayList<>();
   for(Object m:pc.getModelManager().getChildren()){
    if(m.getClass().getSimpleName().matches(".*(Vof|VOF|Multiphase|MultiPhase|Density|Unsteady|Reinitial|Slip|PhaseChange|Cavitation|Evaporation).*"))models.add(inspect(m,6));
    else models.add(Map.of("class",m.getClass().getName()));
   }
   for(Object solver:s.getSolverManager().getChildren())if(solver instanceof ImplicitUnsteadySolver||solver instanceof SegregatedVofSolver||solver.getClass().getSimpleName().matches(".*(SegregatedFlow|Pressure).*"))solvers.add(inspect(solver,5));
   for(Object c:reg.getConditions().getChildren())if(c.getClass().getSimpleName().matches(".*(Source|Wave|Damping|Forcing).*"))sources.add(inspect(c,5));
   for(Object c:reg.getValues().getChildren())if(c.getClass().getSimpleName().matches(".*(Source|Wave|Damping|Forcing).*"))sources.add(inspect(c,5));
   Files.writeString(out.resolve("model_solver_source_settings.json"),json(Map.of("time_s",before,"models",models,"solvers",solvers,"region_sources_and_wave",sources)));
   List<Object> nativeFields=new ArrayList<>();
   for(FieldFunction ff:s.getFieldFunctionManager().getObjects())if((ff.getFunctionName()+" "+ff.getPresentationName()).matches("(?i).*(mass.*(flux|flow|imbalance|residual|conservation)|volume.*(flux|source)|continuity.*(error|residual)).*"))nativeFields.add(inspect(ff,2));
   Files.writeString(out.resolve("native_balance_field_inventory.json"),json(nativeFields));
   List<Object> fresh=new ArrayList<>();double net=0;
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    MassFlowReport q=s.getReportManager().createReport(MassFlowReport.class);q.setPresentationName("Audit_Unsmooth_Mass_"+b.getPresentationName());q.getParts().setObjects(b);
    Map<String,Object> rec=unsmoothed(q);fresh.add(rec);double value=q.getReportMonitorValue();if(!Double.isFinite(value))throw new IllegalStateException("Nonfinite fresh boundary mass report");net+=value;
   }
   FieldFunction rho=s.getFieldFunctionManager().getFunction("Density"),alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
   UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setFunctionName("Audit_Report_Unit");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDefinition("1.0");
   Map<String,Double> integrals=new LinkedHashMap<>();
   FieldFunction[] ffs={rho,alpha,one};String[] names={"Mass_kg","WaterVolume_m3","DomainVolume_m3"};
   for(int i=0;i<ffs.length;i++){
    VolumeIntegralReport q=s.getReportManager().createReport(VolumeIntegralReport.class);q.setPresentationName("Audit_Unsmooth_"+names[i]);q.setFieldFunction(ffs[i]);q.getParts().setObjects(reg);fresh.add(unsmoothed(q));
    double value=q.getReportMonitorValue();if(!Double.isFinite(value))throw new IllegalStateException("Nonfinite fresh volume integral");integrals.put(names[i],value);
   }
   Files.writeString(out.resolve("independent_unsmoothed_reports.json"),json(Map.of("time_s",before,"reports",fresh,"net_outward_mass_kg_s",net,"integrals",integrals)));
   double after=s.getSolution().getPhysicalTime();if(Math.abs(after-before)>1e-12)throw new IllegalStateException("Physical time changed");
   Files.writeString(out.resolve("audit.json"),json(Map.of("status","report_definitions_exported_zero_steps","steps_taken",0,"time_before_s",before,"time_after_s",after,"gpu_count",s.getNumberOfGpgpus(),"cells",fv.getCellCount(),"saved_reports_inspected",oldReports.size(),"net_outward_unsmoothed_kg_s",net,"scope","Diagnostic only: report definitions and independent unsmoothed values; no temporal or physics changes, no simulation state saved")));
  }catch(Exception ex){try{Files.writeString(out.resolve("audit_error.txt"),ex.toString());}catch(Exception ignored){}throw new RuntimeException(ex);}
 }
}
