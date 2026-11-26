package macro;
import star.common.*;
import star.base.report.*;
import star.vis.*;
import java.nio.file.*;

/** 8-step startup smoke test: checks finite values, CFL, wave-zone initialization. */
public class WaveTankSmoke extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path root=Paths.get("F:/ntnu/wave_depth_20261029"),caseDir=root.resolve("W20_H16_X3");
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(caseDir.resolve("built.sim").toAbsolutePath().normalize()))
    throw new IllegalStateException("GUARD: unexpected source");
   if(Files.exists(caseDir.resolve("smoke_history.csv")))throw new IllegalStateException("Preserve earlier smoke run");
   if(s.getSimulationIterator().getCurrentIteration()!=0)throw new IllegalStateException("Source already iterated");
   s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   s.getSimulationIterator().getAutoSave().setEnabled(false);
   Region reg=s.getRegionManager().getRegion("fluid");
   FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()<10000||fv.getCellCount()>1000000)throw new IllegalStateException("Invalid cell count");
   MaxReport vmax=s.getReportManager().createReport(MaxReport.class);
   vmax.setPresentationName("NTNU_Smoke_MaxVelocity");vmax.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());vmax.getParts().setObjects(reg);vmax.setRepresentation(fv);
   MaxReport cfl=s.getReportManager().createReport(MaxReport.class);
   cfl.setPresentationName("NTNU_Smoke_MaxCFL");cfl.setFieldFunction(s.getFieldFunctionManager().getFunction("CourantNumber"));cfl.getParts().setObjects(reg);cfl.setRepresentation(fv);
   s.getSolution().initializeSolution();
   try(var out=Files.newBufferedWriter(caseDir.resolve("smoke_history.csv"))){
    out.write("step,physical_time_s,iteration,max_CFL,max_velocity_mps\n");out.flush();
    for(int step=1;step<=8;step++){
     s.getSimulationIterator().step(1);
     double c=cfl.getReportMonitorValue(),v=vmax.getReportMonitorValue(),t=s.getSolution().getPhysicalTime();
     out.write(step+","+t+","+s.getSimulationIterator().getCurrentIteration()+","+c+","+v+"\n");out.flush();
     if(!Double.isFinite(c)||!Double.isFinite(v)||v>150)throw new IllegalStateException("Bad wave startup cfl="+c+" vmax="+v);
     s.println("[NTNU_WAVE_SMOKE] step="+step+" t="+t+" cfl="+c+" vmax="+v);
    }
   }
   s.saveState(caseDir.resolve("smoke_checkpoint.sim").toString());
   Files.writeString(caseDir.resolve("SMOKE_COMPLETED.txt"),"Eight actual transient time steps completed; not a wave validation.\n");
  }catch(Exception e){throw new RuntimeException("WaveTankSmoke: "+e,e);}
 }
}
