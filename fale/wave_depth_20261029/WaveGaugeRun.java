package macro;
import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.vis.*;
import star.post.*;
import java.nio.file.*;
import java.util.*;
import javax.json.*;

/** Wave gauge test for a pre-meshed, initialized STOKES V tank. Writes a separate history/checkpoint. */
public class WaveGaugeRun extends StarMacro {
 public void execute(){
   Simulation s=getActiveSimulation();
   try{
     Path jp=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_GAUGE_JOB"))).toAbsolutePath().normalize();
     JsonObject job;try(var rd=Json.createReader(Files.newBufferedReader(jp))){job=rd.readObject();}
     Path dir=jp.getParent();
     Path root=Paths.get("F:/ntnu/wave_depth_20261029/fifth_cases").toAbsolutePath().normalize();
     if(!dir.getParent().equals(root)||!Files.exists(dir.resolve("SUCCESS.txt")))throw new IllegalStateException("Unknown case or failed build");
     if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(dir.resolve("built.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Wrong input model");
     Path csv=dir.resolve("gauge_history.csv");
     if(Files.exists(csv))throw new IllegalStateException("Existing gauge results must not be overwritten");
     int steps=job.getInt("steps");
     if(steps<1||steps>50)throw new IllegalArgumentException("Smoke-only run capped at 50 time steps");
     double lam=job.getJsonNumber("lambda_m").doubleValue(),h=job.getJsonNumber("depth_m").doubleValue();
     if(lam<12||lam>40||h<8||h>32)throw new IllegalArgumentException("Invalid wave");
     s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
     s.getSimulationIterator().getAutoSave().setEnabled(false);
     for(SolutionHistory history:s.get(SolutionHistoryManager.class).getSolutionHistories())history.setAutoRecord(false);
     for(Object x:s.getSolverStoppingCriterionManager().getChildren())
       if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
     Region reg=s.getRegionManager().getRegion("fluid");
     FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
     if(fv.getCellCount()<10000||fv.getCellCount()>2000000)throw new IllegalStateException("Invalid cell count");
     FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
     SurfaceIntegralReport gauge0=gauge(s,reg,fv,alpha,"NTNU_eta_x0",0.0);
     SurfaceIntegralReport gauge1=gauge(s,reg,fv,alpha,"NTNU_eta_xHalf",lam/2.0);
     MaxReport cfl=s.getReportManager().createReport(MaxReport.class);cfl.setPresentationName("NTNU_CFLmax");
     cfl.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));cfl.getParts().setObjects(reg);cfl.setRepresentation(fv);
     MaxReport vmax=s.getReportManager().createReport(MaxReport.class);vmax.setPresentationName("NTNU_Vmax");
     vmax.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());vmax.getParts().setObjects(reg);vmax.setRepresentation(fv);
     if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();
     try(var w=Files.newBufferedWriter(csv)){
       w.write("step,t_s,iteration,eta_x0_m,eta_xHalf_m,max_CFL,max_velocity_m_s\n");w.flush();
       for(int step=0;step<=steps;step++){
         if(step>0)s.getSimulationIterator().step(1);
         double e0=gauge0.getReportMonitorValue()/0.8-h,e1=gauge1.getReportMonitorValue()/0.8-h;
         double c=cfl.getReportMonitorValue(),v=vmax.getReportMonitorValue(),t=s.getSolution().getPhysicalTime();
         w.write(step+","+t+","+s.getSimulationIterator().getCurrentIteration()+","+e0+","+e1+","+c+","+v+"\n");w.flush();
         s.println("[NTNU_GAUGE] step="+step+" t="+t+" eta0="+e0+" etaHalf="+e1+" CFL="+c+" vmax="+v);
         if(!(Double.isFinite(e0)&&Double.isFinite(e1)&&Double.isFinite(c)&&Double.isFinite(v))||v>150||Math.abs(e0)>1.5||Math.abs(e1)>1.5)
           throw new IllegalStateException("Unphysical wave startup at step "+step);
       }
     }
     s.saveState(dir.resolve("gauge_checkpoint.sim").toString());
     Files.writeString(dir.resolve("GAUGE_SMOKE_OK.txt"),"Actual transient wave solver completed "+steps+" steps. Not a temporal or wave-height validation.\n");
   }catch(Exception e){throw new RuntimeException("[NTNU_GAUGE] "+e,e);}
 }
 private SurfaceIntegralReport gauge(Simulation s,Region reg,FvRepresentation fv,FieldFunction alpha,String name,double x){
   PlaneSection p=s.getPartManager().createPlaneSection();
   p.setPresentationName(name+"_plane");p.getInputParts().setObjects(reg);
   p.setOrigin(new DoubleVector(new double[]{x,20.4,2.0}));
   p.setOrientation(new DoubleVector(new double[]{1,0,0}));
   SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);
   r.setPresentationName(name+"_alpha_integral");
   r.setFieldFunction(alpha);r.getParts().setObjects(p);r.setRepresentation(fv);
   return r;
 }
}
