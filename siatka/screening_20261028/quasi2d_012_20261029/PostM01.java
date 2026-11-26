package macro;
import star.common.*;import star.vis.*;import java.nio.file.*;import java.util.*;
public class PostM01 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029");
try{
for(String name:List.of("H0_0ms","F18_dt500us")){
Path out=root.resolve("M01").resolve(name);s.loadState(out.resolve("checkpoint.sim").toString());
Region reg=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(reg);tab.setRepresentation(fv);tab.setExtractVertexData(false);
List<FieldFunction> fields=new ArrayList<>();fields.add(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());fields.add(s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(1));
for(String n:List.of("Pressure","Density","CourantNumber"))if(s.getFieldFunctionManager().hasFunction(n))fields.add(s.getFieldFunctionManager().getFunction(n));
StringBuilder fs=new StringBuilder();for(FieldFunction ff:s.getFieldFunctionManager().getObjects())if(ff.getFunctionName().contains("VolumeFraction")){fs.append(ff.getFunctionName()+"\n");if(ff.getFunctionName().toLowerCase().contains("water"))fields.add(ff);}
Files.writeString(out.resolve("volume_fraction_fields.txt"),fs.toString());
tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve("fluid_final_fields.csv").toString());
}
s.loadState(root.resolve("M02/mesh.sim").toString());
}catch(Exception e){throw new RuntimeException(e);}
}}
