package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.vis.*;import star.post.*;
import java.nio.file.*;import java.util.*;
public class ExportFlowFields extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();Path out=Paths.get(System.getenv("NTNU_POST_OUT"));
  try{
   Files.createDirectories(out);double time=s.getSolution().getPhysicalTime();
   if(Math.abs(time-.2)>1e-8)throw new IllegalStateException("Expected pilot checkpoint t=0.2 s");
   Region reg=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   FieldFunction vel=s.getFieldFunctionManager().getFunction("Velocity"),vf=null;
   for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getFunctionName().contains("VolumeFraction")&&f.getFunctionName().contains("water")){vf=f;break;}
   if(vf==null)throw new IllegalStateException("Water fraction unavailable");
   XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(reg);t.setRepresentation(fv);t.setExtractVertexData(false);
   t.setFieldFunctions(List.of(vel.getComponentFunction(0),vel.getComponentFunction(1),vel.getComponentFunction(2),s.getFieldFunctionManager().getFunction("Pressure"),vf,s.getFieldFunctionManager().getFunction("CourantNumber")));
   t.extract();t.export(out.resolve("velocity_vectors.csv").toString());
   Files.writeString(out.resolve("EXPORT_OK.json"),"{\"time_s\":"+time+",\"cells\":"+fv.getCellCount()+",\"solver_steps_taken\":0,\"source_saved\":false}");
  }catch(Exception e){try{Files.writeString(out.resolve("export_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
