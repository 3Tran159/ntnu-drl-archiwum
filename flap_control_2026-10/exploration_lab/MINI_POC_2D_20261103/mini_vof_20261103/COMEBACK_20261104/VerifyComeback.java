package macro;
import star.common.*;import star.flow.*;import star.vof.*;import star.kwturb.*;import star.turbulence.*;
import star.base.report.*;
import java.nio.file.*;
import java.util.*;

public class VerifyComeback extends StarMacro {
 static String profile(Profile p){
  ProfileMethod m=p.getMethod();
  if(m instanceof FunctionScalarProfileMethod sm)return m.getClass().getSimpleName()+":"+sm.getFieldFunction().getPresentationName();
  if(m instanceof FunctionVectorProfileMethod vm)return m.getClass().getSimpleName()+":"+vm.getFieldFunction().getPresentationName();
  if(m instanceof ConstantScalarProfileMethod cm)return m.getClass().getSimpleName()+":"+cm.getQuantity().getSIValue();
  if(m instanceof ConstantVectorProfileMethod cv)return m.getClass().getSimpleName()+":"+cv.getQuantity().getSIVector();
  return m.getClass().getSimpleName();
 }
 static void c01(Simulation s,Path out) throws Exception {
  Region r=s.getRegionManager().getRegion("fluid");
  PhysicsContinuum p=r.getPhysicsContinuum();
  FlatVofWave calm=(FlatVofWave)p.getModelManager().getModel(VofWaveModel.class).getVofWaveManager().getVofWave("Calm");
  List<String> data=new ArrayList<>();
  data.add("start_physical_time_s="+s.getSolution().getPhysicalTime());
  data.add("cells="+((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount());
  data.add("execution_gpu="+s.getNumberOfGpgpus());
  data.add("flat_current="+calm.getCurrent().getSIVector());
  data.add("flat_wind="+calm.getWind().getSIVector());
  data.add("flat_waterline="+calm.getPointOnLevel().getSIVector());
  data.add("ref_p="+p.getReferenceValues().get(ReferencePressure.class).getSIValue());
  data.add("ref_rho="+p.getReferenceValues().get(ReferenceDensity.class).getSIValue());
  data.add("ref_altitude="+p.getReferenceValues().get(ReferenceAltitude.class).getSIVector());
  data.add("gravity="+p.getReferenceValues().get(Gravity.class).getSIVector());
  InitialConditionManager i=p.getInitialConditions();
  data.add("initial_U="+profile(i.get(VelocityProfile.class)));
  data.add("initial_p="+profile(i.get(InitialPressureProfile.class)));
  ProfileMethod alpha=i.get(VolumeFractionProfile.class).getMethod();data.add("initial_alpha="+(alpha instanceof CompositeNMinus1ArrayProfileMethod aa?profile(aa.getProfile(0)):alpha.getClass().getSimpleName()));
  KwTurbSpecOption.Type spec=i.get(KwTurbSpecOption.class).getSelectedElement();
  data.add("initial_turb_spec="+spec);
  if(spec==KwTurbSpecOption.Type.K_OMEGA){
   data.add("initial_k="+profile(i.get(TurbulentKineticEnergyProfile.class)));
   data.add("initial_omega="+profile(i.get(SpecificDissipationRateProfile.class)));
  }else if(spec==KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO){
   data.add("initial_TI="+profile(i.get(TurbulenceIntensityProfile.class)));
   data.add("initial_viscosity_ratio="+profile(i.get(TurbulentViscosityRatioProfile.class)));
  }
  for(Boundary b:r.getBoundaryManager().getBoundaries()){
   String prefix=b.getPresentationName();
   data.add(prefix+".type="+b.getBoundaryType().getClass().getSimpleName());
   if(b.getBoundaryType() instanceof InletBoundary) data.add(prefix+".U="+profile(b.getValues().get(VelocityProfile.class)));
   if(b.getBoundaryType() instanceof PressureBoundary) data.add(prefix+".p="+profile(b.getValues().get(StaticPressureProfile.class)));
  }
  Files.write(out.resolve("C01_NATIVE_READBACK.txt"),data);
  FieldFunctionManager fm=s.getFieldFunctionManager();
  FieldFunction v=fm.getFunction("Velocity");
  XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);
  tab.getParts().setObjects(r);
  tab.setFieldFunctions(List.of(v.getComponentFunction(0),v.getComponentFunction(2),
      fm.getFunction("AbsolutePressure"),fm.getFunction("Pressure"),fm.getFunction("VolumeFractionwater"),
      fm.getFunction("TurbulentKineticEnergy"),fm.getFunction("SpecificDissipationRate")));
  tab.extract();
  tab.export(out.resolve("C01_NATIVE_FIELDS.csv").toString(),",");

  Files.writeString(out.resolve("REOPEN.json"),"{\"time_s\":"+s.getSolution().getPhysicalTime()+",\"steps\":0}");
 }

 static void nwarMesh(Simulation s,Path out,Properties cfg) throws Exception {
  if(!s.getRegionManager().getRegions().isEmpty()||s.getNumberOfGpgpus()!=0)
   throw new IllegalStateException("Fresh CPU-only NWAR import required");
  s.getImportManager().importMeshFiles(cfg.getProperty("nwar_mesh_file"));
  Region region=s.getRegionManager().getRegions().iterator().next();
  FvRepresentation rep=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  long cells=rep.getCellCount();
  if(cells!=Long.parseLong(cfg.getProperty("expected_cells")))throw new IllegalStateException("NWAR mesh count mismatch");
  for(String field:List.of("Volume","CellQuality","FaceValidity","Position")){
   FieldFunction f=s.getFieldFunctionManager().getFunction(field);
   if(f==null)throw new IllegalStateException("Missing mesh field "+field);
  }
  List<String> lines=new ArrayList<>();
  for(Boundary b:region.getBoundaryManager().getBoundaries())lines.add(b.getPresentationName());
  Files.write(out.resolve("NWAR_NATIVE_BOUNDARIES.txt"),lines);
  var report=rep.generateMeshReport(List.of(region));
  Files.writeString(out.resolve("NWAR_NATIVE_REPORT.txt"),report.toFormattedString());
  long negative=Long.parseLong(String.valueOf(report.get("NegativeVolumeCells")));
  long unclosed=Long.parseLong(String.valueOf(report.get("UnclosedCells")));
  long degenerate=Long.parseLong(String.valueOf(report.get("DegeneratedFeCells")));
  String joined=String.join(" ",lines).toLowerCase(Locale.ROOT);
  boolean pass=negative==0&&unclosed==0&&degenerate==0
   &&joined.contains("hf_012_main")&&joined.contains("hf_012_flap")
   &&joined.contains("q2d_span_source")&&joined.contains("q2d_span_target");
  s.saveState(out.resolve("NWAR_MESH_ONLY.sim").toString());
  Files.writeString(out.resolve("REOPEN.json"),"{\"steps\":0,\"cells\":"+cells+",\"negative_volumes\":"+negative+
    ",\"unclosed_cells\":"+unclosed+",\"degenerate_cells\":"+degenerate+",\"pass\":"+pass+"}");
 }
 public void execute() {
  Simulation s=getActiveSimulation();
  try {
   Path out=Path.of(System.getenv("MINI_CASE_DIR"));
   Properties cfg=new Properties();
   try(var r=Files.newBufferedReader(out.resolve("job.properties"))){cfg.load(r);}
   if(cfg.containsKey("nwar_mesh_file")){nwarMesh(s,out,cfg);return;}
   Path expected=out.resolve("input.sim").toAbsolutePath().normalize();
   if(!Path.of(s.getSessionPath()).toAbsolutePath().normalize().equals(expected))
    throw new IllegalStateException("Unexpected verification input");

   if(Boolean.parseBoolean(cfg.getProperty("c01_audit","false"))){c01(s,out);return;}
   if(Boolean.parseBoolean(cfg.getProperty("cfl_probe","false"))){
    Region region=s.getRegionManager().getRegions().iterator().next();
    FieldFunctionManager fm=s.getFieldFunctionManager();
    FieldFunction position=fm.getFunction("Position"),velocity=fm.getFunction("Velocity"),cfl=fm.getFunction("CourantNumber");
    List<FieldFunction> samples=new ArrayList<>(List.of(position.getComponentFunction(0),position.getComponentFunction(1),position.getComponentFunction(2),
     velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),fm.getFunction("Volume")));
    MaxReport max=s.getReportManager().createReport(MaxReport.class);
    max.setFieldFunction(cfl);max.getParts().setObjects(region);max.setSmooth(false);max.setCollocatedFieldFunctions(samples);
    double value=max.getReportMonitorValue();
    StringBuilder report=new StringBuilder("field,value\n");
    report.append("max_CFL,").append(value).append("\n");
    for(FieldFunction sample:samples)
     report.append(sample.getPresentationName()).append(",").append(max.getCollocatedValue(sample)).append("\n");
    Files.writeString(out.resolve("CFL_MAX_COLLOCATION.csv"),report.toString());
    XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);
    tab.getParts().setObjects(region);
    List<FieldFunction> export=new ArrayList<>();export.add(cfl);export.addAll(samples.subList(3, samples.size()));
    for(String field:List.of("Pressure","TurbulentKineticEnergy","SpecificDissipationRate")) export.add(fm.getFunction(field)); tab.setFieldFunctions(export);tab.extract();tab.export(out.resolve("cell_cfl.csv").toString(),",");
    Files.writeString(out.resolve("REOPEN.json"),"{\"time_s\":"+s.getSolution().getPhysicalTime()+",\"diagnostic\":\"CFL read only\",\"steps\":0}");
    return;
   }
   XyzInternalTable f=(XyzInternalTable)s.getTableManager().getTable("NIGHT_FIELDS");
   f.extract();
   f.export(out.resolve("reopened_fields.csv").toString(),",");
   StringBuilder normal=new StringBuilder("monitor,normalization_type,factor,normalized,samples,last_stored\n");
   for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r){
    double[] history=r.getAllYValues();
    normal.append(r.getPresentationName()).append(",").append(r.getNormalizationType().getClass().getSimpleName()).append(",")
     .append(r.getNormalizationType().getNormalizationFactor()).append(",").append(r.isNormalized()).append(",")
     .append(history.length).append(",").append(history.length==0?Double.NaN:history[history.length-1]).append("\n");
   }
   Files.writeString(out.resolve("RESIDUAL_NORMALIZATION.csv"),normal.toString());
   double t=s.getSolution().getPhysicalTime();
   long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
   Files.writeString(out.resolve("REOPEN.json"),"{\"time_s\":"+t+",\"cells\":"+cells+"}");
  }catch(Exception e){throw new RuntimeException(e);}
 }
}



