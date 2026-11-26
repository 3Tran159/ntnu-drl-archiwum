package macro;

import java.nio.file.*;
import java.util.*;
import star.base.report.*;
import star.common.*;
import star.flow.*;
import star.motion.*;
import star.vof.*;

public class AuditW03Copy extends StarMacro {
 public void execute() {
  try {
   Simulation s=getActiveSimulation();
   Path out=Path.of(System.getenv("FLAP_BENCH_DIR"));
   FvRepresentation mesh=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   Region reg=s.getRegionManager().getRegion("fluid");
   Boundary foil=reg.getBoundaryManager().getBoundary("HF_012_wall");
   List<String> lines=new ArrayList<>();
   lines.add("time_s="+s.getSolution().getPhysicalTime());
   lines.add("cells="+mesh.getCellCount());
   lines.add("motion="+reg.getValues().get(MotionSpecification.class).getMotion().getPresentationName());
   for(Boundary b:reg.getBoundaryManager().getBoundaries())lines.add("boundary="+b.getPresentationName()+":"+b.getBoundaryType().getClass().getSimpleName());
   for(var m:reg.getPhysicsContinuum().getModelManager().getObjects())lines.add("model="+m.getClass().getSimpleName());
   for(ManagedVofWave wave:reg.getPhysicsContinuum().getModelManager().getModel(VofWaveModel.class).getVofWaveManager().getObjects())
    lines.add("wave="+wave.getPresentationName()+":"+wave.getClass().getSimpleName());
   var report=mesh.generateMeshReport(List.of(reg));
   Files.writeString(out.resolve("W03_MESH_REPORT.txt"),report.toFormattedString());
   Files.write(out.resolve("W03_NATIVE_READBACK.txt"),lines);
   FieldFunction p=s.getFieldFunctionManager().getFunction("Position");
   XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);
   tab.getParts().setObjects(foil);
   tab.setExtractVertexData(true);
   tab.setFieldFunctions(List.of(p.getComponentFunction(0),p.getComponentFunction(1),p.getComponentFunction(2)));
   tab.extract();
   tab.export(out.resolve("W03_FOIL_VERTICES.csv").toString(),",");
  } catch(Exception e) { throw new RuntimeException(e); }
 }
}
