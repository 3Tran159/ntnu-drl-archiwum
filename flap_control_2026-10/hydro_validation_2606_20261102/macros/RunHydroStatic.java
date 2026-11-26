package macro;
import star.common.*;import java.nio.file.*;import java.io.*;
public class RunHydroStatic extends StarMacro {
Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),scripts;Simulation s;
void child(String name,Path input)throws Exception {
 if(!Files.isRegularFile(input)||!input.toAbsolutePath().normalize().startsWith(root.resolve("cases")))throw new IllegalStateException("Owned checkpoint required");
 System.setProperty("NTNU_HYDRO_INPUT_OVERRIDE",input.toString());
 StarScript script=new StarScript(s,scripts.resolve(name).toFile());script.play();
 if(script.getInterruptedByException())throw new IllegalStateException("Child macro failed: "+name);
}
public void execute(){s=getActiveSimulation();String id=System.getenv("NTNU_HYDRO_RUN_ID"),variant=System.getenv("NTNU_HYDRO_VARIANT");Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),base=input.getParent(),audit=base.resolve("pipeline_"+id);try{
 if(!input.startsWith(root.resolve("cases")))throw new IllegalStateException("Working case only");String name=input.getFileName().toString();if(!((variant.equals("SP_B")&&name.equals("SP_B_mesh_ready.sim"))||(variant.equals("SP_C")&&(name.equals("motion_verified.sim")||name.equals("pose_ready.sim")||(name.equals("steady_checkpoint.sim")&&Files.readString(base.resolve("initialization_status.json")).contains("steady_initialization_incomplete"))))))throw new IllegalStateException("Pipeline requires a prepared pose or incomplete steady initializer; never a physical-time URANS checkpoint");scripts=Paths.get(System.getenv("NTNU_HYDRO_MACRO_DIR"));Files.createDirectories(audit);
 child("InitializeHydroControl.java",input);
 Path init=base.resolve("steady_init_"+id),ready=init.resolve("URANS_ready.sim");String status=Files.readString(init.resolve("initialization_status.json"));
 if(!status.contains("steady_force_windows_passed")||!Files.exists(ready)){Files.writeString(audit.resolve("status.json"),"{\"status\":\"initialization_gate_not_passed\",\"next_started\":false,\"training_approved\":false}");return;}
 child("StabilizeHydro.java",ready);
 Path run=init.resolve("stabilize_"+id);String finalStatus=Files.readString(run.resolve("status.json"));
 Files.writeString(audit.resolve("status.json"),finalStatus);
 Files.writeString(audit.resolve("paths.txt"),"Initialized state: "+ready+"\nTransient result: "+run+"\nSource preserved: "+input+"\n");
 s.println("HYDRO_PIPELINE "+variant+" "+finalStatus);
}catch(Exception e){try{Files.createDirectories(audit);Files.writeString(audit.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
finally{System.clearProperty("NTNU_HYDRO_INPUT_OVERRIDE");}
}
}
