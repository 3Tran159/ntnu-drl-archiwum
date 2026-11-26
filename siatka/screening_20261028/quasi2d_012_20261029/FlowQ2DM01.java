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

public class FlowQ2DM01 extends StarMacro {
  private Simulation s; private Path root;
  private Region fluid; private Boundary foil; private FvRepresentation fv;
  private ForceReport fx,fz; private MaxReport vmax,cfl,ymax; private MinReport ymin; private AreaAverageReport ymean;
  private FlatVofWave calm; private ImplicitUnsteadySolver unsteady;
  private final double area=.0238,volume=.0023158194813401897;
  public void execute(){s=getActiveSimulation();root=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M01");
    try {
      s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);s.getSimulationIterator().getAutoSave().setEnabled(false);
      for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
      PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
      calm=(FlatVofWave)pc.getModelManager().getModel(VofWaveModel.class).getVofWaveManager().getVofWave("Calm");
      unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);unsteady.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.FIRST_ORDER);
      fluid=s.getRegionManager().getRegion("fluid");foil=fluid.getBoundaryManager().getBoundary("HF_012_wall");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
      if(fv.getCellCount()<=0 || fv.getCellCount()>1000000)throw new IllegalStateException("Wrong mesh");
      String iv=pc.getInitialConditions().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction().getPresentationName();
      String bv=fluid.getBoundaryManager().getBoundary("DOMAIN.inlet").getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction().getPresentationName();
      if(!iv.equals("Velocity of Calm")||!bv.equals(iv))throw new IllegalStateException("Unexpected initial/inlet velocity: "+iv+" / "+bv);
      // Copy the already-defined Calm phase fraction to pressure-outlet backflow.
      VolumeFractionProfile inletVF=fluid.getBoundaryManager().getBoundary("DOMAIN.inlet").getValues().get(VolumeFractionProfile.class);
      FieldFunction water=inletVF.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
      VolumeFractionProfile outletVF=fluid.getBoundaryManager().getBoundary("DOMAIN.outlet").getValues().get(VolumeFractionProfile.class);
      outletVF.setMethod(CompositeNMinus1ArrayProfileMethod.class);
      outletVF.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);
      outletVF.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(water);
      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
      fx=(ForceReport)s.getReportManager().getReport("Fx_half");fz=(ForceReport)s.getReportManager().getReport("Fz_half");
      for(ForceReport f:List.of(fx,fz)){f.getParts().setObjects(foil);f.setRepresentation(fv);}
      vmax=s.getReportManager().createReport(MaxReport.class);vmax.setPresentationName("Short_MaxVelocity");vmax.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());vmax.getParts().setObjects(fluid);vmax.setRepresentation(fv);
      cfl=s.getReportManager().createReport(MaxReport.class);cfl.setPresentationName("Short_MaxCFL");cfl.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));cfl.getParts().setObjects(fluid);cfl.setRepresentation(fv);
      ymean=s.getReportManager().createReport(AreaAverageReport.class);ymean.setPresentationName("Short_MeanYplus");
      ymax=s.getReportManager().createReport(MaxReport.class);ymax.setPresentationName("Short_MaxYplus");
      ymin=s.getReportManager().createReport(MinReport.class);ymin.setPresentationName("Short_MinYplus");
      for(ScalarReport r:List.of(ymean,ymax,ymin)){r.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));r.getParts().setObjects(foil);r.setRepresentation(fv);}
      for(Report r:List.of(vmax,cfl,ymean,ymax,ymin))r.createMonitor();
      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(20);((SolverStoppingCriterion)x).setIsUsed(true);}
      boolean hydro=stage("H0_0ms",0,1e-4,120,200);
      if(hydro && !Files.exists(root.resolve("STOP_ALL"))){stage("F18_dt100us",18,1e-4,180,200);stage("F18_dt500us",18,5e-4,180,40);}
      else Files.writeString(root.resolve("F18_SKIPPED.txt"),"Hydrostatic run triggered a stability/stop guard. Review H0 before flow.");
      Files.writeString(root.resolve("sequence_completed.json"),json(Map.of("status","sequence_finished","flow_attempted",hydro&&!Files.exists(root.resolve("STOP_ALL")))));
    }catch(Exception e){try{Files.writeString(root.resolve("macro_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
  }
  private boolean stage(String name,double u,double dt,double seconds,int maxSteps)throws Exception {
    Path out=root.resolve(name);Files.createDirectories(out);
    if(Files.exists(out.resolve("history.csv")))throw new IllegalStateException("Preserve previous history");
    calm.getCurrent().setComponents(u,0,0);calm.getWind().setComponents(u,0,0);
    unsteady.getTimeStep().setValue(dt);
    s.getSolution().clearSolutionWithoutMeshReset();
    if(fv.getCellCount()<=0 || fv.getCellCount()>1000000)throw new IllegalStateException("Mesh changed on reset");
    double rho=calm.getHeavyFluidDensity().getSIValue(),buoyancy=rho*9.81*volume;
    Map<String,Object> setup=new LinkedHashMap<>();
    setup.put("case",name);setup.put("geometry","Q2D_constant_verified_012");setup.put("cells",fv.getCellCount());setup.put("speed_m_s",u);setup.put("dt_s",dt);setup.put("workers",s.getNumberOfWorkers());
    setup.put("rho_kg_m3",rho);setup.put("S_ref_slice_m2",area);setup.put("expected_hydrostatic_Fz_N",buoyancy);setup.put("temporal_order","FIRST_ORDER");setup.put("wall_budget_s",seconds);setup.put("max_steps",maxSteps);
    setup.put("outlet_phase_backflow","Calm volume fraction, copied from inlet; previous constant zero replaced");
    setup.put("force_convention","Fx +X; Fz +Z; pressure+shear; No Correction includes buoyancy. CL_total includes buoyancy.");
    setup.put("purpose","Short startup diagnostic, not converged forces or wave validation");
    Files.writeString(out.resolve("setup.json"),json(setup));
    s.getSolution().initializeSolution();
    if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Time not reset");
    s.saveState(out.resolve("prepared.sim").toString());
    long start=System.nanoTime(),saved=start;int steps=0;String status="wall_budget_completed";boolean good=true;double maxSeen=0;
    try(var w=Files.newBufferedWriter(out.resolve("history.csv"))){
      w.write("wall_seconds,step,iteration,physical_time_s,dt_s,Fx_slice_N,Fz_slice_N,max_velocity_m_s,max_convective_CFL,foil_mean_yplus,foil_min_yplus,foil_max_yplus,CD,CL_total,CL_buoyancy_subtracted,buoyancy_error_pct\n");
      while((System.nanoTime()-start)*1e-9<seconds && steps<maxSteps){
        if(Files.exists(root.resolve("STOP_ALL"))||Files.exists(out.resolve("STOP"))){status="stopped_by_marker";good=false;break;}
        double before=s.getSolution().getPhysicalTime();s.getSimulationIterator().step(1);steps++;
        double a=fx.getReportMonitorValue(),b=fz.getReportMonitorValue(),v=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),ym=ymean.getReportMonitorValue(),yl=ymin.getReportMonitorValue(),yh=ymax.getReportMonitorValue(),t=s.getSolution().getPhysicalTime();
        double wall=(System.nanoTime()-start)*1e-9,q=.5*rho*u*u*area;
        String coefficients=u>0?(a/q)+","+(b/q)+","+((b-buoyancy)/q):",,";
        w.write(wall+","+steps+","+s.getSimulationIterator().getCurrentIteration()+","+t+","+dt+","+a+","+b+","+v+","+co+","+ym+","+yl+","+yh+","+coefficients+","+((b-buoyancy)/buoyancy*100)+"\n");w.flush();
        maxSeen=Math.max(maxSeen,v);s.println("[SHORT012] "+name+" step="+steps+" t="+t+" wall="+wall+" vmax="+v+" CFL="+co);
        if(t<=before||!Double.isFinite(a)||!Double.isFinite(b)||!Double.isFinite(v)||!Double.isFinite(co)||!Double.isFinite(ym)||v>(u==0?5:180)){status="unstable_or_no_progress";good=false;break;}
        if((System.nanoTime()-saved)*1e-9>90){s.saveState(out.resolve("checkpoint.sim").toString());saved=System.nanoTime();}
      }
    }
    if(steps>=maxSteps)status="step_budget_completed";
    double solverWall=(System.nanoTime()-start)*1e-9;
    s.saveState(out.resolve("checkpoint.sim").toString());
    try {exportDiagnostics(out);}catch(Exception e){Files.writeString(out.resolve("diagnostic_export_error.txt"),e.toString());}
    Files.writeString(out.resolve("completed.json"),json(Map.of("status",status,"steps",steps,"physical_time_s",s.getSolution().getPhysicalTime(),"solver_wall_seconds",solverWall,"peak_velocity_m_s",maxSeen,"guard_passed",good,"checkpoint",out.resolve("checkpoint.sim").toString())));
    return good;
  }
  private void exportDiagnostics(Path out)throws Exception{
    XyzInternalTable wall=s.getTableManager().createTable(XyzInternalTable.class);wall.getParts().setObjects(foil);wall.setRepresentation(fv);wall.setExtractVertexData(false);
    List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("WallYplus","Pressure","PrismLayerNumber","PrismCellThickness"))fields.add(s.getFieldFunctionManager().getFunction(name));
    wall.setFieldFunctions(fields);wall.extract();wall.export(out.resolve("foil_final_fields.csv").toString());
    for(Monitor monitor:s.getMonitorManager().getObjects()){try{monitor.export(out.resolve("monitor_"+monitor.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}catch(Exception ignored){}}
    ThresholdPart high=s.getPartManager().createThresholdPart();high.getInputParts().setObjects(fluid);high.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));high.setRange(new DoubleVector(new double[]{5,5}));high.setMode(ThresholdMode.ABOVE_TAG);
    ElementCountReport count=s.getReportManager().createReport(ElementCountReport.class);count.getParts().setObjects(high);count.setRepresentation(fv);double n=count.getReportMonitorValue();
    Files.writeString(out.resolve("cfl_diagnostic.json"),json(Map.of("threshold",5,"comparison",">","cell_count",n)));
    if(n>0&&n<100000){XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(high);table.setRepresentation(fv);table.setExtractVertexData(false);fields=new ArrayList<>();for(String name:List.of("CourantNumber","CellQuality","SkewnessAngle","VolumeChange","PrismLayerNumber"))fields.add(s.getFieldFunctionManager().getFunction(name));table.setFieldFunctions(fields);table.extract();table.export(out.resolve("cfl_above_5_locations.csv").toString());}
  }
  private static String json(Object o){
    if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();
    if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
    if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)o)j.add(json(x));return j.toString();}
    return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
  }
}