package macro;
import star.common.*;import star.flow.*;import star.vof.*;import star.segregatedflow.*;import star.base.neo.*;import star.base.report.*;
import java.nio.file.*;import java.util.*;
/** Explicit local input inspection. CPU1 only. ZERO FLOW: never initialize, clear, step or run. */
public class InspectLocalMesh extends StarMacro {
 private Simulation s;private Path out;
 private static String json(Object o){if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)o)j.add(json(x));return j.toString();}return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";}
 private void write(String n,Object x)throws Exception{Files.writeString(out.resolve(n),json(x));}
 private double scalar(String name,boolean max,Region reg,FvRepresentation fv){
  ScalarReport q=max?s.getReportManager().createReport(MaxReport.class):s.getReportManager().createReport(MinReport.class);
  q.setPresentationName("Import inspection "+name);q.setFieldFunction(s.getFieldFunctionManager().getFunction(name));q.setRepresentation(fv);q.setSmooth(false);q.getParts().setObjects(reg);double v=q.getReportMonitorValue();
  if(!Double.isFinite(v)||!q.getErrorLog().isBlank())throw new IllegalStateException("Cannot evaluate mesh field "+name+": "+q.getErrorLog());return v;
 }
 private List<Double> vector(VectorPhysicalQuantity q){DoubleVector v=q.getSIVector();return List.of(v.get(0),v.get(1),v.get(2));}
 public void execute(){
  s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_MESH_IMPORT_OUT")));
  try{
   if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Inspection requires CPU/noGPU");
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Only immutable disposable copy may be inspected");
   double before=s.getSolution().getPhysicalTime();if(!Double.isFinite(before)||before<0)throw new IllegalStateException("Invalid physical time");
   if(s.getRegionManager().getRegions().size()!=1)throw new IllegalStateException("Expected one fluid region; prepare a single-region quasi-2D input");
   Region reg=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   long cells=fv.getCellCount();if(cells<=0)throw new IllegalStateException("No volume mesh: generate the mesh and save a .sim first");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   Map<String,Object> d=new LinkedHashMap<>(),quality=new LinkedHashMap<>(),profile=new LinkedHashMap<>();
   ArrayList<String> configuration=new ArrayList<>(),replacement=new ArrayList<>();ArrayList<Object> boundaries=new ArrayList<>();Set<String> names=new TreeSet<>();
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){names.add(b.getPresentationName());Map<String,Object> q=new LinkedHashMap<>();q.put("name",b.getPresentationName());q.put("type",b.getBoundaryType().getClass().getSimpleName());boundaries.add(q);}
   Set<String> expected=new TreeSet<>(List.of("DOMAIN.inlet","DOMAIN.outlet","DOMAIN.top","DOMAIN.bottom","HF_012_wall","Q2D_span_source","Q2D_span_target"));
   if(!names.equals(expected))throw new IllegalStateException("Unsupported boundary names. Required: "+expected+"; found: "+names);
   NeoProperty mr=fv.generateMeshReport(List.of(reg));Files.writeString(out.resolve("mesh_report.txt"),mr.toFormattedString());
   for(String k:List.of("NegativeVolumeCells","UnclosedCells","DegeneratedFeCells"))quality.put(k,mr.get(k));
   quality.put("min_cell_quality",scalar("CellQuality",false,reg,fv));quality.put("min_face_validity",scalar("FaceValidity",false,reg,fv));quality.put("max_skewness_angle_deg",scalar("SkewnessAngle",true,reg,fv));
   try{ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);profile.put("dt_s",us.getTimeStep().getValue());profile.put("order",String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()));}catch(Exception e){configuration.add("Configure Implicit Unsteady SECOND_ORDER with dt0.0001..0.001s");}
   try{Integer inner=null;for(Object o:s.getSolverStoppingCriterionManager().getChildren())if(o instanceof InnerIterationStoppingCriterion){inner=((Number)o.getClass().getMethod("getMaximumNumberInnerIterations").invoke(o)).intValue();}profile.put("inner",inner);if(inner==null)configuration.add("Inner-iteration criterion unavailable");}catch(Exception e){configuration.add("Could not read inner-iteration criterion: "+e.getClass().getSimpleName());}
   try{PhysicsContinuum pc=reg.getPhysicsContinuum();profile.put("continuum",pc.getPresentationName());profile.put("models",pc.getModelManager().getObjects().toString());
    VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);profile.put("vof_wave_model_available",wm!=null);profile.put("calm_flat_reference_available",wm.getVofWaveManager().getObject("Calm") instanceof FlatVofWave);
    if(!pc.getPresentationName().equals("water+air"))configuration.add("Continuum must be named water+air for the local recipe");
    ManagedVofWave wave=reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();profile.put("forcing_reference_type",wave.getClass().getSimpleName());profile.put("current_m_s",vector((VectorPhysicalQuantity)wave.getClass().getMethod("getCurrent").invoke(wave)));profile.put("wind_m_s",vector((VectorPhysicalQuantity)wave.getClass().getMethod("getWind").invoke(wave)));profile.put("waterline_m",vector((VectorPhysicalQuantity)wave.getClass().getMethod("getPointOnLevel").invoke(wave)));profile.put("vertical",vector((VectorPhysicalQuantity)wave.getClass().getMethod("getVerticalDirection").invoke(wave)));profile.put("wave_active",!(wave instanceof FlatVofWave));
    if(!(wave instanceof FlatVofWave))replacement.add("Input contains a wave reference. A separate controlled calm preparation is required; retained fields are not accepted C01.");
   }catch(Exception e){replacement.add("Existing forcing reference unavailable; new C01 preparation must bind Calm: "+e.getClass().getSimpleName());}
   try{profile.put("pressure_AMG_tolerance",s.getSolverManager().getSolver(SegregatedFlowSolver.class).getPressureSolver().getAMGLinearSolver().getConvergeTol());profile.put("VOF_AMG_tolerance",s.getSolverManager().getSolver(SegregatedVofSolver.class).getAMGLinearSolver().getConvergeTol());profile.put("segregated_flow_vof_available",true);for(AMGLinearSolver a:List.of(s.getSolverManager().getSolver(SegregatedFlowSolver.class).getPressureSolver().getAMGLinearSolver(),s.getSolverManager().getSolver(SegregatedVofSolver.class).getAMGLinearSolver()))if(a.getMaxCycles()!=30||a.getEpsilon()!=0)configuration.add("Required source pressure/VOF AMG maxCycles30 epsilon0 unavailable");}catch(Exception e){configuration.add("Pressure/VOF solver configuration unavailable");}
   try{profile.put("outlet_reversed_pressure",String.valueOf(reg.getBoundaryManager().getBoundary("DOMAIN.outlet").getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()));
    profile.put("bottom_shear",String.valueOf(reg.getBoundaryManager().getBoundary("DOMAIN.bottom").getConditions().get(WallShearStressOption.class).getSelectedElement()));
    profile.put("foil_shear",String.valueOf(reg.getBoundaryManager().getBoundary("HF_012_wall").getConditions().get(WallShearStressOption.class).getSelectedElement()));
    profile.put("top_reversed_pressure",String.valueOf(reg.getBoundaryManager().getBoundary("DOMAIN.top").getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()));
   }catch(Exception e){replacement.add("Boundary condition configuration will be applied in new C01 copy; existing getters unavailable: "+e.getClass().getSimpleName());}
   ImportManager im=s.getImportManager();im.setFormatType(SolutionExportFormat.Type.CGNS);
   im.export(out.resolve("mesh.CGNS").toString(),List.of(reg),List.of(s.getFieldFunctionManager().getFunction("CellQuality")),List.of());
   if(Math.abs(s.getSolution().getPhysicalTime()-before)>1e-12)throw new IllegalStateException("Physical time changed during zero-flow inspection");
   s.saveState(out.resolve("inspected.sim").toString());
   d.put("schema_version",1);d.put("status","zero_flow_inspection_completed");d.put("cells",cells);d.put("physical_time_s",before);d.put("physical_time_after_s",s.getSolution().getPhysicalTime());d.put("flow_steps",0);d.put("initialized_or_cleared",false);d.put("gpu_count",0);d.put("quality",quality);d.put("boundaries",boundaries);d.put("profile",profile);d.put("configuration_notes",configuration);d.put("settings_to_replace_notes",replacement);d.put("retained_fields_are_accepted_calm",false);d.put("scientific_approval","not_assessed");write("inspection.json",d);
  }catch(Exception e){try{write("inspection_error.json",Map.of("status","inspection_failed","error",e.toString(),"flow_steps",0,"physical_time_s",s.getSolution().getPhysicalTime()));}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
