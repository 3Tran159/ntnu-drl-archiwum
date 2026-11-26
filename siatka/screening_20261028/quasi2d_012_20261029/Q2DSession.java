package macro;
import star.common.*;
import java.nio.file.*;
import java.util.*;
public class Q2DSession extends StarMacro {
public void execute(){
Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029");
long start=System.currentTimeMillis(),last=start;Set<String> seen=new HashSet<>();
try{
while(System.currentTimeMillis()-start<10800000 && System.currentTimeMillis()-last<1800000 && !Files.exists(root.resolve("END_SESSION"))){
 if(Files.exists(root.resolve("commands.txt")))for(String line:Files.readAllLines(root.resolve("commands.txt"))){
  String name=line.trim();if(name.isEmpty()||seen.contains(name))continue;seen.add(name);last=System.currentTimeMillis();
  s.println("[Q2D_SESSION] RUN "+name);Files.writeString(root.resolve("active_command.txt"),name);
  try{StarScript script=new StarScript(s,root.resolve(name).toFile());script.play();Files.writeString(root.resolve(name+".done"),"interrupted_by_exception="+script.getInterruptedByException());}
  catch(Exception e){Files.writeString(root.resolve(name+".error"),e.toString());s.println("[Q2D_SESSION] ERROR "+e);}
  Files.deleteIfExists(root.resolve("active_command.txt"));last=System.currentTimeMillis();
 }
 Thread.sleep(1000);
}
Files.writeString(root.resolve("session_completed.txt"),"Session ended");
}catch(Exception e){throw new RuntimeException(e);}
}}
