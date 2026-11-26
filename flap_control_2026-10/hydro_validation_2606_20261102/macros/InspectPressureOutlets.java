package macro;
import star.common.*;import star.flow.*;import star.metrics.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class InspectPressureOutlets extends StarMacro {
Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;
String directionName(int n){for(BackflowVelocityDirectionOption.Type t:BackflowVelocityDirectionOption.Type.values())if(t.getValue()==n)return t.name();return "UNKNOWN_"+n;}
void inspectBackflow(Object o,String bucket,StringBuilder b){
 if(o instanceof BackflowSpecification){BackflowSpecification v=(BackflowSpecification)o;int n=v.getBackflowVelocityDirectionOption().getSelected();b.append("backflow_bucket="+bucket+"\nbackflow_direction_value="+n+"\nbackflow_direction_name="+directionName(n)+"\nbackflow_pressure_option="+v.getReversedFlowPressureOption().getSelected()+"\nbackflow_scalar_option="+v.getReversedFlowScalarOption().getSelected()+"\n");}
}
String fingerprint(Path p)throws Exception{java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream stream=Files.newInputStream(p)){byte[] chunk=new byte[1048576];int n;while((n=stream.read(chunk))!=-1)md.update(chunk,0,n);}return java.util.HexFormat.of().formatHex(md.digest());}
public void execute(){s=getActiveSimulation();Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();String variant=System.getenv("NTNU_HYDRO_VARIANT");out=root.resolve("audit/pressure_outlets_"+variant+"_"+System.getenv("NTNU_HYDRO_RUN_ID"));try{
Path b=root.resolve("cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim");
Path c=root.resolve("cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433/checkpoint.sim");
if(!input.equals(b)&&!input.equals(c))throw new IllegalStateException("Exact owned read-only source required");
Files.createDirectories(out);if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json"))||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Pause/CPU-only guard");
s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
String expected=input.equals(b)?"5f9a86e51f8eb96cc1adb0fd36a61ae48e015600512598517b6ec2f6c9190ff1":"8b6162b9baa27a5e04c38048dbab3c801cdd99266200a320231390d1f3f8feed";if(!fingerprint(input).equals(expected))throw new IllegalStateException("Source fingerprint changed");
double t0=s.getSolution().getPhysicalTime();int it0=s.getSimulationIterator().getCurrentIteration();long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
StringBuilder text=new StringBuilder("source="+input+"\nphysical_time_s="+t0+"\nnative_iteration="+it0+"\ncells="+cells+"\nNO_SOLVER_STEPS_NO_SIM_SAVE\n");int outlets=0;
for(Region r:s.getRegionManager().getRegions())if(r.getPhysicsContinuum()!=null&&r.getPhysicsContinuum().getPresentationName().equals("HYDRO water SST singlephase"))for(Boundary wall:r.getBoundaryManager().getBoundaries())if(wall.getBoundaryType() instanceof PressureBoundary){
outlets++;text.append("\nREGION="+r.getPresentationName()+"\nBOUNDARY="+wall.getPresentationName()+"\ntype="+wall.getBoundaryType()+"\n");
for(Object o:wall.getConditions().getObjects()){text.append("condition_class="+o.getClass().getName()+"\n");inspectBackflow(o,"conditions",text);}
for(Object o:wall.getValues().getObjects()){text.append("value_class="+o.getClass().getName()+"\n");inspectBackflow(o,"values",text);}
ScalarProfile pressure=wall.getValues().get(StaticPressureProfile.class);text.append("static_pressure_method="+pressure.getMethod().getClass().getSimpleName()+"\n");
if(pressure.getMethod() instanceof FunctionScalarProfileMethod){FieldFunction ff=pressure.getMethod(FunctionScalarProfileMethod.class).getFieldFunction();text.append("pressure_field="+ff.getFunctionName()+"\n");if(ff instanceof UserFieldFunction)text.append("pressure_definition="+((UserFieldFunction)ff).getDefinition()+"\n");}
}
if(outlets!=2)throw new IllegalStateException("Expected top and downstream pressure outlets; found"+outlets);
if(s.getSolution().getPhysicalTime()!=t0||s.getSimulationIterator().getCurrentIteration()!=it0)throw new IllegalStateException("Read-only counters changed");
if(!fingerprint(input).equals(expected))throw new IllegalStateException("Source changed during inspection");Files.writeString(out.resolve("source_sha256_before_after.txt"),expected+"\nunchanged=true\n");
Files.writeString(out.resolve("pressure_outlet_setup.txt"),text.toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"sim_saved\":false,\"source_time_s\":"+t0+",\"source_native_iteration\":"+it0+",\"scientific_approved\":false}");
s.println("PRESSURE_OUTLET_INSPECTION_COMPLETE_NO_SOLVER_STEPS_NO_SIM_SAVE");
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_failed\",\"solver_steps\":0,\"sim_saved\":false}");}catch(Exception ignored){}throw new RuntimeException(e);}
}
}
