package macro;
import star.common.*;
import star.vof.*;
import star.base.neo.*;
import star.base.report.*;
import star.flow.*;
import star.post.*;
import star.vis.*;
import java.nio.file.*;
import java.util.*;
import javax.json.*;

/** Identical calm-water stability runs on isolated mesh cases, bounded by wall time. */
public class NightCFD extends StarMacro {
  private Simulation s;private Path out;private final List<ScalarReport> diagnostics=new ArrayList<>();
  public void execute(){s=getActiveSimulation();try{
    Path jobPath=Paths.get(Objects.requireNonNull(System.getenv("NTNU_CFD_JOB")));
    JsonObject job;try(var r=Json.createReader(Files.newBufferedReader(jobPath))){job=r.readObject();}
    Path source=Paths.get(job.getString("source")).toAbsolutePath().normalize();out=Paths.get(job.getString("output")).toAbsolutePath().normalize();
    if(!out.startsWith(Paths.get("E:/ntnu_cfd_night_20261028"))||!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(source))throw new IllegalStateException("Source/output guard");
    Files.createDirectories(out);if(Files.exists(out.resolve("history.csv")))throw new IllegalStateException("Preserve previous run history");
    s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);s.getSimulationIterator().getAutoSave().setEnabled(false);
    // Do not append to inherited external .simh files; checkpoints stay case-local.
    for(SolutionHistory history:s.get(SolutionHistoryManager.class).getSolutionHistories())history.setAutoRecord(false);
    PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
    FlatVofWave calm=(FlatVofWave)pc.getModelManager().getModel(VofWaveModel.class).getVofWaveManager().getVofWave("Calm");
    calm.getCurrent().setComponents(18,0,0);calm.getWind().setComponents(18,0,0);
    ImplicitUnsteadySolver unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
    if(Math.abs(unsteady.getTimeStep().getSIValue()-1e-5)>1e-12)throw new IllegalStateException("Unexpected timestep");
    // Retain temporal order, inner-iteration criteria, turbulence and all mesh settings.
    for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
    Region fluid=s.getRegionManager().getRegion("fluid");Boundary foil=fluid.getBoundaryManager().getBoundary("HF_v2 2.ColoredFace1");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
    if(fv.getCellCount()<=0||fv.getCellCount()>35000000)throw new IllegalStateException("Cell budget");
    ForceReport fx=(ForceReport)s.getReportManager().getReport("Fx_half");ForceReport fz=(ForceReport)s.getReportManager().getReport("Fz_half");fx.setRepresentation(fv);fz.setRepresentation(fv);
    MaxReport vmax=s.getReportManager().createReport(MaxReport.class);vmax.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());vmax.getParts().setObjects(fluid);vmax.setRepresentation(fv);
    MaxReport cfl=s.getReportManager().createReport(MaxReport.class);cfl.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));cfl.getParts().setObjects(fluid);cfl.setRepresentation(fv);
    AreaAverageReport yp=s.getReportManager().createReport(AreaAverageReport.class);yp.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));yp.getParts().setObjects(foil);yp.setRepresentation(fv);
    Files.writeString(out.resolve("setup.json"),"{\"speed_m_s\":18,\"water_current\":[18,0,0],\"air_velocity\":[18,0,0],\"time_step_s\":1e-5,\"temporal_order\":\""+unsteady.getTimeDiscretizationOption()+"\",\"cells\":"+fv.getCellCount()+",\"workers\":"+s.getNumberOfWorkers()+",\"purpose\":\"initial stability and resource screening, not converged forces\"}");
    s.saveState(out.resolve("prepared.sim").toString());
    if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();
    long started=System.nanoTime(),saved=started;int steps=0;double limit=job.getJsonNumber("wall_seconds").doubleValue();int maxSteps=job.getInt("max_steps",10000000);String status="wall_budget_completed";
    try(var writer=Files.newBufferedWriter(out.resolve("history.csv"))){writer.write("wall_seconds,iteration,physical_time_s,Fx_half_N,Fz_half_N,max_velocity_m_s,max_convective_CFL,foil_mean_yplus\n");writer.flush();
      while((System.nanoTime()-started)*1e-9<limit&&steps<maxSteps){
        if(Files.exists(out.resolve("STOP"))||Files.exists(out.getParent().resolve("STOP_ALL"))){status="stopped_by_marker";break;}
        int before=s.getSimulationIterator().getCurrentIteration();s.getSimulationIterator().step(1);steps++;
        int iter=s.getSimulationIterator().getCurrentIteration();double t=s.getSolution().getPhysicalTime();double a=fx.getReportMonitorValue(),b=fz.getReportMonitorValue(),v=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),y=yp.getReportMonitorValue();
        if(iter<=before||!Double.isFinite(a)||!Double.isFinite(b)||!Double.isFinite(v)||!Double.isFinite(co)||!Double.isFinite(y)||v>180){status="unstable_or_no_progress";break;}
        double wall=(System.nanoTime()-started)*1e-9;writer.write(wall+","+iter+","+t+","+a+","+b+","+v+","+co+","+y+"\n");writer.flush();s.println("[NTNU] CFD_PROGRESS steps="+steps+" iteration="+iter+" t="+t+" wall="+wall+" vmax="+v);
        if((System.nanoTime()-saved)*1e-9>=900){s.saveState(out.resolve("checkpoint.sim").toString());saved=System.nanoTime();}
      }
    }
    if(steps>=maxSteps&&status.equals("wall_budget_completed"))status="step_budget_completed";
    s.saveState(out.resolve("checkpoint.sim").toString());
    // Optional diagnostics cannot erase a valid checkpoint or disguise the solver status.
    try{exportDiagnostics(foil,fluid,fv);}catch(Exception ex){Files.writeString(out.resolve("diagnostic_export_error.txt"),ex.toString());}
    Files.writeString(out.resolve("completed.json"),"{\"status\":\""+status+"\",\"outer_calls\":"+steps+",\"iterations\":"+s.getSimulationIterator().getCurrentIteration()+",\"physical_time_s\":"+s.getSolution().getPhysicalTime()+",\"wall_seconds\":"+(System.nanoTime()-started)*1e-9+"}");
  }catch(Exception e){throw new RuntimeException(e);}}
  private void exportDiagnostics(Boundary foil,Region fluid,FvRepresentation fv)throws Exception{
    XyzInternalTable wall=s.getTableManager().createTable(XyzInternalTable.class);wall.getParts().setObjects(foil);wall.setRepresentation(fv);wall.setExtractVertexData(false);
    List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("WallYplus","Pressure","PrismLayerNumber","PrismCellThickness"))fields.add(s.getFieldFunctionManager().getFunction(name));
    wall.setFieldFunctions(fields);wall.extract();wall.export(out.resolve("foil_final_fields.csv").toString());
    ThresholdPart high=s.getPartManager().createThresholdPart();high.getInputParts().setObjects(fluid);high.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));high.setRange(new DoubleVector(new double[]{5,5}));high.setMode(ThresholdMode.ABOVE_TAG);
    ElementCountReport count=s.getReportManager().createReport(ElementCountReport.class);count.getParts().setObjects(high);count.setRepresentation(fv);double n=count.getReportMonitorValue();
    Files.writeString(out.resolve("cfl_diagnostic.json"),"{\"threshold\":5,\"comparison\":\">\",\"cell_count\":"+n+",\"note\":\"diagnostic trigger, not a universal stability limit\"}");
    if(n>0&&n<100000){XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(high);table.setRepresentation(fv);table.setExtractVertexData(false);fields=new ArrayList<>();for(String name:List.of("CourantNumber","CellQuality","SkewnessAngle","VolumeChange","PrismLayerNumber"))fields.add(s.getFieldFunctionManager().getFunction(name));table.setFieldFunctions(fields);table.extract();table.export(out.resolve("cfl_above_5_locations.csv").toString());}
  }
}
