package macro;
import star.common.*;
import star.meshing.*;
import star.cadmodeler.*;
import java.nio.file.*;
import java.util.*;
public class ImportVerified012 extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path audit=Paths.get("F:/ntnu/mesh_screening_20261028/block1_20261029");
  Path output=Paths.get("F:/ntnu/geometry_012_20261029");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(audit.resolve("source_copy.sim").toAbsolutePath().normalize()))throw new RuntimeException("Wrong source");
  s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  s.getSimulationIterator().getAutoSave().setEnabled(false);
  SolidModelPart old=(SolidModelPart)s.getGeometryPartManager().getPart("HF_v2");
  Set<GeometryPart> before=new HashSet<>(s.getGeometryPartManager().getParts());
  s.get(PartImportManager.class).importCadPart(output.resolve("HF_012_v3.x_t").toString(),"SharpEdges",30.0,4,1e-8);
  List<CadPart> added=new ArrayList<>();
  for(GeometryPart p:s.getGeometryPartManager().getParts())if(!before.contains(p)&&p instanceof CadPart)added.add((CadPart)p);
  if(added.size()!=1)throw new RuntimeException("Unexpected imported body count");
  CadPart cad=added.get(0);cad.setPresentationName("HF_012_v3");
  cad.getTessellationDensityOption().setSelected(TessellationDensityOption.Type.USER_DEFINED);
  TessellationParameters tp=cad.getTessellationDensityOption().getDetailedParameters();
  tp.setIsCurveChordTolerancePercentage(false);tp.setIsSurfacePlaneTolerancePercentage(false);
  tp.setCurveChordTolerance(1e-5);tp.setSurfacePlaneTolerance(1e-5);
  tp.setCurveChordAngle(0.5);tp.setSurfacePlaneAngle(0.5);
  cad.getTessellationDensityOption().setDetailedParameters(tp);cad.tessellate();
  cad.exportStlPart(output.resolve("star_012_verified_m.stl").toString(),false);
  SubtractPartsOperation subtract=(SubtractPartsOperation)s.get(MeshOperationManager.class).getObject("Subtract");
  MeshPart domain=(MeshPart)s.getGeometryPartManager().getPart("DOMAIN");
  subtract.getInputGeometryObjects().setObjects(domain,cad);subtract.setTargetPart(domain);subtract.execute();
  MeshOperationPart fluidPart=(MeshOperationPart)s.getGeometryPartManager().getPart("Subtract");
  List<PartSurface> foilSurfaces=new ArrayList<>();
  for(PartSurface ps:fluidPart.getPartSurfaceManager().getPartSurfaces()){
   s.println("[NTNU] OUTPUT_SURFACE "+ps.getPresentationName());
   if(ps.getPresentationName().contains("HF_012_v3"))foilSurfaces.add(ps);
  }
  if(foilSurfaces.isEmpty())throw new RuntimeException("No corrected foil surfaces in Boolean output");
  AutoMeshOperation mesh=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Automated Mesh");
  ((SurfaceCustomMeshControl)mesh.getCustomMeshControls().getObject("HF_surface")).getGeometryObjects().setObjects(foilSurfaces);
  List<PartCurve> foilCurves=new ArrayList<>();
  for(PartCurve pc:fluidPart.getPartCurveManager().getPartCurves())if(pc.getPresentationName().contains("HF_012_v3"))foilCurves.add(pc);
  if(foilCurves.isEmpty())throw new RuntimeException("No corrected foil edges");
  ((CurveCustomMeshControl)mesh.getCustomMeshControls().getObject("Curve Control")).getGeometryObjects().setObjects(foilCurves);
  Boundary wall=s.getRegionManager().getRegion("fluid").getBoundaryManager().getBoundary("HF_v2 2.ColoredFace1");
  wall.getPartSurfaceGroup().setObjects(foilSurfaces);
  old.setPresentationName("ARCHIVE_010_INACTIVE");
  old.getCadModel().setPresentationName("ARCHIVE_010_INACTIVE");
  fluidPart.exportStlPart(output.resolve("fluid_012_boolean_m.stl").toString(),false);
  for(Boundary b:s.getRegionManager().getRegion("fluid").getBoundaryManager().getBoundaries())
   s.println("[NTNU] BOUNDARY "+b.getPresentationName()+" surfaces="+b.getPartSurfaceGroup().getObjects());
  s.println("[NTNU] ACTIVE_SUBTRACT_INPUTS "+subtract.getInputGeometryObjects().getObjects());
  s.saveState(output.resolve("HF_012_baseline_unmeshed.sim").toString());
  s.println("[NTNU] CORRECTED_CAD_IMPORTED_BOUND_AND_BASELINE_SAVED");
 }
}