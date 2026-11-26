package macro;
import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.flow.*;
import star.vof.*;
import star.vis.*;
import star.post.*;
import java.nio.file.*;
import java.util.*;

public class ContinueForces extends StarMacro {
  private Simulation s; private Path out; private Region fluid; private Boundary foil; private FvRepresentation fv;
  private ForceReport fx,fz,pressure,shear; private MaxReport vmax,cfl,interfaceCfl; private AreaAverageReport yplus;
  private double dt,target,startTime; private int inner;
  public void execute() {
    s=getActiveSimulation();
    out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_STAB_OUT")));
    try {
      dt=Double.parseDouble(System.getenv("NTNU_STAB_DT"));
      target=Double.parseDouble(System.getenv("NTNU_STAB_TARGET"));
      inner=Integer.parseInt(System.getenv("NTNU_STAB_INNER"));
      long expectedCells=Long.parseLong(System.getenv("NTNU_STAB_CELLS"));
      double expectedStart=Double.parseDouble(System.getenv("NTNU_STAB_START"));
      String order=System.getenv("NTNU_STAB_ORDER");
      double budget=Double.parseDouble(System.getenv("NTNU_STAB_BUDGET"));
      if(Files.exists(out.resolve("history.csv"))) throw new IllegalStateException("History exists; use a new attempt directory");
      s.getSimulationIterator().getAutoSave().setEnabled(false);
      s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
      for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
      fluid=s.getRegionManager().getRegion("fluid"); foil=fluid.getBoundaryManager().getBoundary("HF_012_wall");
      fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
      if(fv.getCellCount()!=expectedCells)throw new IllegalStateException("Mesh identity mismatch: "+fv.getCellCount());
      if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("One active GPU required");
      startTime=s.getSolution().getPhysicalTime();
      if(Math.abs(startTime-expectedStart)>dt*.1)throw new IllegalStateException("Unexpected restart time "+startTime);
      PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
      FlatVofWave calm=(FlatVofWave)pc.getModelManager().getModel(VofWaveModel.class).getVofWaveManager().getVofWave("Calm");
      double rho=calm.getHeavyFluidDensity().getSIValue();
      if(Math.abs(rho-1000)>1e-6)throw new IllegalStateException("Unexpected reference density");
      ImplicitUnsteadySolver unsteady=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
      unsteady.getTimeStep().setValue(dt);
      unsteady.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.valueOf(order));
      for(Object x:s.getSolverStoppingCriterionManager().getChildren()) {
        if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
        if(x instanceof InnerIterationStoppingCriterion) {((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(inner);((SolverStoppingCriterion)x).setIsUsed(true);}
      }
      fx=force("Stab_Drag",new double[]{1,0,0},ForceReportForceOption.Type.PRESSURE_AND_SHEAR);
      fz=force("Stab_Lift",new double[]{0,0,1},ForceReportForceOption.Type.PRESSURE_AND_SHEAR);
      pressure=force("Stab_PressureDrag",new double[]{1,0,0},ForceReportForceOption.Type.PRESSURE);
      shear=force("Stab_ViscousDrag",new double[]{1,0,0},ForceReportForceOption.Type.SHEAR);
      vmax=max("Stab_MaxVelocity",s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction(),fluid);
      cfl=max("Stab_MaxCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),fluid);
      yplus=s.getReportManager().createReport(AreaAverageReport.class);yplus.setPresentationName("Stab_MeanYplus");
      yplus.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));yplus.getParts().setObjects(foil);yplus.setRepresentation(fv);yplus.createMonitor();
      FieldFunction vf=null;
      for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getFunctionName().contains("VolumeFraction")&&f.getFunctionName().contains("water")) {vf=f;break;}
      if(vf==null)throw new IllegalStateException("Water volume fraction unavailable");
      ThresholdPart inter=s.getPartManager().createThresholdPart();inter.setPresentationName("Stab_Interface");
      inter.getInputParts().setObjects(fluid);inter.setFieldFunction(vf);inter.setRange(new DoubleVector(new double[]{.01,.99}));inter.setMode(ThresholdMode.BETWEEN_TAG);
      interfaceCfl=max("Stab_InterfaceCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),inter);
      List<String> bounds=new ArrayList<>();
      for(Boundary b:fluid.getBoundaryManager().getBoundaries())bounds.add(b.getPresentationName()+": "+b.getBoundaryType().getClass().getName());
      Map<String,Object> audit=new LinkedHashMap<>();
      audit.put("cells",fv.getCellCount());audit.put("start_time_s",startTime);audit.put("target_time_s",target);audit.put("dt_s",dt);
      audit.put("order",order);audit.put("inner_iterations",inner);audit.put("gpu_count",s.getNumberOfGpgpus());audit.put("rho",rho);
      audit.put("current",calm.getCurrentVector().toString());audit.put("wind",calm.getWindVector().toString());audit.put("waterline",calm.getPointOnLevelVector().toString());
      audit.put("boundaries",bounds);audit.put("reference_area_m2",.0238);audit.put("span_m",.02);
      audit.put("models",pc.getModelManager().getObjects().toString());audit.put("purpose","Continuation without resetting solution; stabilization screen, not validation");
      Files.writeString(out.resolve("setup.json"),json(audit));
      s.saveState(out.resolve("restart_prepared.sim").toString());
      long start=System.nanoTime();int steps=0;String state="target_reached";
      try(var w=Files.newBufferedWriter(out.resolve("history.csv"))) {
        w.write("wall_seconds,step,iteration,physical_time_s,dt_s,Fx_slice_N,Fz_slice_N,pressure_drag_N,viscous_drag_N,CD,CL_total,max_velocity_m_s,max_CFL,interface_max_CFL,mean_yplus\n");
        while(s.getSolution().getPhysicalTime()<target-dt*.1) {
          if(Files.exists(out.resolve("STOP"))||Files.exists(out.getParent().resolve("STOP_ALL"))) {state="stopped_by_marker";break;}
          if((System.nanoTime()-start)*1e-9>budget) {state="wall_budget";break;}
          double before=s.getSolution().getPhysicalTime();s.getSimulationIterator().step(1);steps++;
          double t=s.getSolution().getPhysicalTime(),d=fx.getReportMonitorValue(),l=fz.getReportMonitorValue(),p=pressure.getReportMonitorValue(),v=shear.getReportMonitorValue();
          double speed=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),ci=interfaceCfl.getReportMonitorValue(),yp=yplus.getReportMonitorValue();
          double wall=(System.nanoTime()-start)*1e-9,q=.5*rho*18*18*.0238;
          w.write(wall+","+steps+","+s.getSimulationIterator().getCurrentIteration()+","+t+","+dt+","+d+","+l+","+p+","+v+","+d/q+","+l/q+","+speed+","+co+","+ci+","+yp+"\n");w.flush();
          if(!Double.isFinite(d)||!Double.isFinite(l)||!Double.isFinite(speed)||!Double.isFinite(co)||!Double.isFinite(ci)||speed>90||Math.abs(d)>2000||Math.abs(l)>20000||t<=before) {state="stability_guard";break;}
          if(Math.abs(d-p-v)>Math.max(.01,Math.abs(d)*1e-4))throw new IllegalStateException("Pressure/shear force sum failed");
          if(steps%10==0)Files.writeString(out.resolve("progress.json"),json(Map.of("time_s",t,"steps",steps,"wall_s",wall,"CD",d/q,"CL_total",l/q,"CFL",co,"interface_CFL",ci)));
          if(steps%100==0) {
            String name=String.format(Locale.ROOT,"checkpoint_t%.3f.sim",t);
            s.saveState(out.resolve(name).toString());
            Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("path",out.resolve(name).toString(),"time_s",t)));
          }
        }
      }
      for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof PhysicalTimeStoppingCriterion) {
        ((PhysicalTimeStoppingCriterion)x).getMaximumTime().setValue(s.getSolution().getPhysicalTime()+.05);((SolverStoppingCriterion)x).setIsUsed(true);
      }
      s.saveState(out.resolve("final.sim").toString());
      Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("path",out.resolve("final.sim").toString(),"time_s",s.getSolution().getPhysicalTime())));
      exportFields(vf);
      Files.writeString(out.resolve("completed.json"),json(Map.of("status",state,"steps",steps,"time_s",s.getSolution().getPhysicalTime(),"solver_wall_s",(System.nanoTime()-start)*1e-9)));
    } catch(Exception e) {
      try {Files.writeString(out.resolve("macro_error.txt"),e.toString());}catch(Exception ignored){}
      throw new RuntimeException(e);
    }
  }
  private ForceReport force(String name,double[] dir,ForceReportForceOption.Type type) {
    ForceReport f=s.getReportManager().createReport(ForceReport.class);f.setPresentationName(name);f.getDirection().setComponents(dir[0],dir[1],dir[2]);f.getParts().setObjects(foil);f.setRepresentation(fv);f.getForceOption().setSelected(type);f.createMonitor();return f;
  }
  private MaxReport max(String name,FieldFunction ff,NamedObject part) {
    MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setPresentationName(name);r.setFieldFunction(ff);r.getParts().setObjects(part);r.setRepresentation(fv);r.createMonitor();return r;
  }
  private void exportFields(FieldFunction vf)throws Exception {
    fx.printReport(out.resolve("drag_pressure_shear.txt").toString(),false);fz.printReport(out.resolve("lift_pressure_shear.txt").toString(),false);
    XyzInternalTable wall=s.getTableManager().createTable(XyzInternalTable.class);wall.getParts().setObjects(foil);wall.setRepresentation(fv);wall.setExtractVertexData(false);
    wall.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("WallYplus")));wall.extract();wall.export(out.resolve("foil_fields.csv").toString());
    XyzInternalTable cells=s.getTableManager().createTable(XyzInternalTable.class);cells.getParts().setObjects(fluid);cells.setRepresentation(fv);cells.setExtractVertexData(false);
    cells.setFieldFunctions(List.of(vf,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction()));cells.extract();cells.export(out.resolve("fluid_fields.csv").toString());
    for(Monitor m:s.getMonitorManager().getObjects())try{m.export(out.resolve("monitor_"+m.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}catch(Exception ignored){}
  }
  private static String json(Object o) {
    if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();
    if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
    if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)o)j.add(json(x));return j.toString();}
    return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
  }
}
