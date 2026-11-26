package macro;
import star.common.*;import star.meshing.*;import java.nio.file.*;
public class ExportReferenceGeometry extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path r=Paths.get("C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_drl_20261102");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(r.resolve("04_cases/calm/FLAP_C00_seed.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable seed required");
  if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU inspection only");
  for(String n:new String[]{"Q2D_foil","HF_012_v3"}){
   GeometryPart p=s.getGeometryPartManager().getPart(n);
   if(!(p instanceof MeshPart))throw new IllegalStateException("Exportable native mesh part required: "+n);
   ((MeshPart)p).exportStlPart(r.resolve("02_geometry/"+n+"_reference.stl").toString(),false);
  }
  try{Files.writeString(r.resolve("00_audit/geometry_export_complete.txt"),"Native tessellation exported; no simulation steps or saves.\n");}catch(Exception e){throw new RuntimeException(e);}
  s.println("FLAP_REFERENCE_EXPORT_COMPLETE");
 }
}