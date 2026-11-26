package macro;
import star.common.*;import star.meshing.*;import java.nio.file.*;
public class RecoverFlapPOC extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/flap_control/flap_poc_2606_20261102");
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("FlapPOC_2606_mesh_ready.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Owned coarse mesh required");
   AutoMeshOperation bg=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Coarse background");
   AutoMeshOperation ov=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Coarse overset");
   bg.getDefaultValues().get(BaseSize.class).setValue(.12);ov.getDefaultValues().get(BaseSize.class).setValue(.018);
   bg.execute();ov.execute();
   long n=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
   Files.writeString(out.resolve("audit/cell_count.txt"),Long.toString(n));
   Files.writeString(out.resolve("audit/coarsening.txt"),"Initial 82018 cells; increased cell sizes before any motion/flow tests. Final cells="+n+"\n");
   s.saveState(out.resolve("FlapPOC_2606_mesh_ready.sim").toString());
   StarScript test=new StarScript(s,out.resolve("macros/TestFlapPOC.java").toFile());test.play();
   if(test.getInterruptedByException())throw new IllegalStateException("Motion test macro failed");
  }catch(Exception e){try{Files.writeString(out.resolve("audit/recovery_error.txt"),e.toString());}catch(Exception ignore){}throw new RuntimeException(e);}
 }
}
