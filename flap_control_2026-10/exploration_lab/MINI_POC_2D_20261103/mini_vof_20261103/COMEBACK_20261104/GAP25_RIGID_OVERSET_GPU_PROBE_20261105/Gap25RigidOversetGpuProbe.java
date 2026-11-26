package macro;

import java.nio.file.*;
import star.common.*;
import star.motion.*;

public class Gap25RigidOversetGpuProbe extends StarMacro {
 public void execute() {
  Simulation s=getActiveSimulation();
  Path d=Path.of(System.getenv("FLAP_BENCH_DIR"));
  try{
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("One GPU required");
   double start=s.getSolution().getPhysicalTime();
   if(Math.abs(start-.65)>1e-9)throw new IllegalStateException("Wrong source checkpoint");
   FvRepresentation mesh=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(mesh.getCellCount()!=333939)throw new IllegalStateException("Wrong source mesh");
   Region overset=s.getRegionManager().getRegion("FlapOverset");
   RotatingMotion rotation=(RotatingMotion)overset.getValues().get(MotionSpecification.class).getMotion();
   RotationAngle angle=(RotationAngle)rotation.getRotationSpecification();
   if(!angle.getRotationAngle().getDefinition().equals("<0 deg>"))throw new IllegalStateException("Flap is not at 0 deg");
   angle.getRotationAngle().setDefinition("<2 deg>*sin(2*3.141592653589793*($Time-<"+start+" s>)/<0.2 s>)");
   s.getSimulationIterator().getAutoSave().setEnabled(false);
   s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){
    if(c instanceof PhysicalTimeStoppingCriterion||c instanceof StepStoppingCriterion)c.setIsUsed(false);
    if(c instanceof InnerIterationStoppingCriterion){
     ((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(12);
     c.setIsUsed(true);
    }
   }
   s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(.002);
   Files.writeString(d.resolve("STATUS.txt"),"FIRST_STEP\ncells=333939\nangle_range_deg=-2,+2\ntime_s="+start+"\n");
   s.saveState(d.resolve("GAP25_RIGID_CONFIGURED.sim").toString());
   s.getSimulationIterator().step(1);
   double now=s.getSolution().getPhysicalTime();
   if(Math.abs(now-start-.002)>1e-9)throw new IllegalStateException("No completed physical step");
   Files.writeString(d.resolve("STATUS.txt"),"STEP_COMPLETED\nsteps=1\ntime_s="+now+"\n");
   s.saveState(d.resolve("ONE_STEP.sim").toString());
  }catch(Exception e){
   try{Files.writeString(d.resolve("ERROR.txt"),e.toString()+"\ntime_s="+s.getSolution().getPhysicalTime());}catch(Exception ignored){}
   throw new RuntimeException(e);
  }
 }
}
