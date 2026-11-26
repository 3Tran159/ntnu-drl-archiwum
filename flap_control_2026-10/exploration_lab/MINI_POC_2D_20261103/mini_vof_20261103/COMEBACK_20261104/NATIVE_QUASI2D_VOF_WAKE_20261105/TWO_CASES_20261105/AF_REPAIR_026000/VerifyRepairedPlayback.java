import java.nio.file.*;
import java.util.*;
import star.common.*;
import star.post.*;
import star.vis.*;

public class VerifyRepairedPlayback extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path out=Paths.get(System.getenv("AF_REPAIR_DIR"));
  try{
   if(Math.abs(s.getSolution().getPhysicalTime()-.026)>1e-9)throw new IllegalStateException("Wrong physical time");
   RecordedSolutionView view=(RecordedSolutionView)s.get(SolutionViewManager.class).getObject("AF - Repaired Playback");
   SolutionHistory h=view.getSolutionHistory();h.rescanFile();
   if(h.getNumberOfStates()<2)throw new IllegalStateException("Saved history not readable");
   for(int n=0;n<2;n++){
    view.setStateIndex(h.getMinStateIndex()+n);
    for(Scene scene:s.getSceneManager().getScenes()){
     String name=scene.getPresentationName();
     if(name.startsWith("AF REPAIRED ")&&!name.startsWith("AF REPAIRED 05")){
      if(scene.getDisplayerManager().getObjects().stream().noneMatch(pd->view.getRepresentation().equals(pd.getRepresentation())))
       throw new IllegalStateException("Scene lost recorded representation "+name);
      scene.printAndWait(out.resolve("REOPEN_"+n+"_"+name.substring(12,14)+".png").toString(),1,880,500);
     }
    }
   }
   Files.writeString(out.resolve("REOPEN_OK.txt"),"frames="+h.getNumberOfStates()+"\nverified_state_indices=0,1\nCFD_steps=0\n");
  }catch(Exception e){throw new RuntimeException(e);}
 }
}

