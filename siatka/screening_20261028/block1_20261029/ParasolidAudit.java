package macro;
import star.common.*;
import star.meshing.*;
import java.nio.file.*;
import java.util.*;
public class ParasolidAudit extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path out=Paths.get("F:/ntnu/mesh_screening_20261028/block1_20261029");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("source_copy.sim").toAbsolutePath().normalize()))throw new RuntimeException("Wrong source");
  s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  s.getSimulationIterator().getAutoSave().setEnabled(false);
  Set<GeometryPart> before=new HashSet<>(s.getGeometryPartManager().getParts());
  s.get(PartImportManager.class).importCadPart("F:/ntnu/HF_v2.x_t","SharpEdges",30.0,4,1e-8);
  int count=0;
  for(GeometryPart p:s.getGeometryPartManager().getParts()){
   if(!before.contains(p)&&p instanceof CadPart){
    CadPart cad=(CadPart)p;
    cad.getTessellationDensityOption().setSelected(TessellationDensityOption.Type.VERY_FINE);
    cad.tessellate();
    cad.exportStlPart(out.resolve("parasolid_direct_"+count+".stl").toString(),false);
    s.println("[NTNU] PARASOLID_DIRECT "+p.getPresentationName()); count++;
   }
  }
  if(count!=1)throw new RuntimeException("Expected one imported CAD body, got "+count);
  s.println("[NTNU] PARASOLID_AUDIT_COMPLETE");
 }
}