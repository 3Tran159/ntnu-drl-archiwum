package macro;
import star.common.*;
import star.base.report.*;
import star.motion.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
/** Inspects only the disposable seed. No steps, saves, initialization or setters. */
public class InspectFlapSeed extends StarMacro {
 private String value(Object object,String method) {
  try{return String.valueOf(object.getClass().getMethod(method).invoke(object));}
  catch(Exception e){return "<unavailable>";}
 }
 public void execute() {
  Simulation s=getActiveSimulation();
  Path root=Paths.get("F:/ntnu/flap_control/flap_drl_20261102");
  Path expected=root.resolve("04_cases/calm/FLAP_C00_seed.sim").toAbsolutePath().normalize();
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(expected))
   throw new IllegalStateException("Disposable seed required");
  StringBuilder b=new StringBuilder("session="+s.getSessionPath()+"\ntime_s="+s.getSolution().getPhysicalTime()+"\n");
  for(Representation rep:s.getRepresentationManager().getObjects())
   if(rep instanceof FvRepresentation)b.append("mesh="+rep.getPresentationName()+" cells="+((FvRepresentation)rep).getCellCount()+"\n");
  for(Continuum c:s.getContinuumManager().getObjects()) {
   b.append("continuum="+c.getPresentationName()+" class="+c.getClass().getName()+"\n");
   if(c instanceof PhysicsContinuum)b.append("models="+((PhysicsContinuum)c).getModelManager().getObjects()+"\n");
  }
  for(Region r:s.getRegionManager().getRegions()) {
   b.append("region="+r.getPresentationName()+"\n");
   for(Boundary x:r.getBoundaryManager().getBoundaries())
    b.append(" boundary="+x.getPresentationName()+" type="+x.getBoundaryType().getClass().getSimpleName()+" surfaces="+x.getPartSurfaceGroup().getObjects()+"\n");
  }
  for(GeometryPart p:s.getGeometryPartManager().getLeafParts())
   b.append("geometry="+p.getPresentationName()+" class="+p.getClass().getName()+"\n");
  for(Report r:s.getReportManager().getObjects()) {
   b.append("report="+r.getPresentationName()+" class="+r.getClass().getName());
   for(String k:new String[]{"getDirection","getOrigin","getParts","getDefinition","getReferenceArea","getReferenceDensity","getReferenceVelocity","getForceOption","getUnits","getCoordinateSystem"})
    {String v=value(r,k);if(!v.equals("<unavailable>"))b.append(" "+k+"="+v);}
   b.append("\n");
  }
  for(Motion m:s.get(MotionManager.class).getObjects())
   b.append("motion="+m.getPresentationName()+" class="+m.getClass().getName()+"\n");
  for(Solver solver:s.getSolverManager().getObjects())
   b.append("solver="+solver.getPresentationName()+" class="+solver.getClass().getName()+"\n");
  try{Files.writeString(root.resolve("00_audit/seed_inspection.txt"),b.toString());}
  catch(Exception e){throw new RuntimeException(e);}
  s.println("FLAP_SEED_READ_ONLY_INSPECTION_COMPLETE");
 }
}
