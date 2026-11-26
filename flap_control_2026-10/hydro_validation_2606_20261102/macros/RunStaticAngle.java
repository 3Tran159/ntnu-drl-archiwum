package macro;
import star.common.*;import java.nio.file.*;import java.io.*;
public class RunStaticAngle extends StarMacro {
Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),scripts;Simulation s;
void child(String name,Path input)throws Exception{
 if(!Files.isRegularFile(input)||!input.toAbsolutePath().normalize().startsWith(root.resolve("cases/SP_C_split0_overset")))throw new IllegalStateException("Owned C checkpoint required");
 System.setProperty("NTNU_HYDRO_INPUT_OVERRIDE",input.toString());StarScript macro=new StarScript(s,scripts.resolve(name).toFile());macro.play();
 if(macro.getInterruptedByException())throw new IllegalStateException("Child failed: "+name);
}
public void execute(){s=getActiveSimulation();String id=System.getenv("NTNU_HYDRO_RUN_ID");double angle=Double.parseDouble(System.getenv("NTNU_HYDRO_ANGLE_DEG"));Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),audit=root.resolve("cases/SP_C_split0_overset/angle_pipeline_"+id);try{
 if(!ListHolder.allowed(angle)||!Files.readString(input.getParent().resolve("status.json")).contains("force_stabilization_passed"))throw new IllegalStateException("Approved angle and stabilized physical parent required");
 scripts=Paths.get(System.getenv("NTNU_HYDRO_MACRO_DIR"));Files.createDirectories(audit);
 child("PrepareStaticFlap.java",input);
 Path pose=root.resolve("cases/SP_C_split0_overset/static_"+(angle<0?"minus":"plus")+Math.round(Math.abs(angle))+"_"+id).resolve("pose_ready.sim");
 if(!Files.exists(pose))throw new IllegalStateException("Pose checkpoint absent");
 child("InitializeHydroControl.java",pose);
 Path init=pose.getParent().resolve("steady_init_"+id),ready=init.resolve("URANS_ready.sim");
 if(!Files.exists(ready)||!Files.readString(init.resolve("initialization_status.json")).contains("steady_force_windows_passed")){Files.writeString(audit.resolve("status.json"),"{\"status\":\"initialization_gate_not_passed\",\"training_approved\":false}");return;}
 child("StabilizeHydro.java",ready);
 Path run=init.resolve("stabilize_"+id);Files.writeString(audit.resolve("status.json"),Files.readString(run.resolve("status.json")));
 Files.writeString(audit.resolve("paths.txt"),"Source: "+input+"\nPose: "+pose+"\nResult: "+run+"\nAngle: "+angle+"\n");
}catch(Exception e){try{Files.createDirectories(audit);Files.writeString(audit.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
finally{System.clearProperty("NTNU_HYDRO_INPUT_OVERRIDE");}}
static class ListHolder{static boolean allowed(double angle){return angle==2||angle==-2||angle==5||angle==-5;}}
}
