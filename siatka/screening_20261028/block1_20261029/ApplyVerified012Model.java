package macro;
import star.common.*;
import star.meshing.*;
import star.cadmodeler.*;
import star.cadmodeler.ui.ModelReImportCommands;
import java.util.*;
import java.nio.file.*;
public class ApplyVerified012Model extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path audit=Paths.get("F:/ntnu/mesh_screening_20261028/block1_20261029");
  Path output=Paths.get("F:/ntnu/geometry_012_20261029");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(audit.resolve("source_copy.sim").toAbsolutePath().normalize()))throw new RuntimeException("Wrong source");
  s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  s.getSimulationIterator().getAutoSave().setEnabled(false);
  CadPart cad=(CadPart)s.getGeometryPartManager().getPart("HF_v2");
  CadModel model=((SolidModelPart)cad).getCadModel();
  ImportCadFileFeature imported=null;
  for(Feature f:model.getFeatureManager().getFeatures()){
   s.println("[NTNU] CAD_FEATURE "+f.getPresentationName()+" "+f.getClass().getName());
   if(f instanceof ImportCadFileFeature){if(imported!=null)throw new RuntimeException("Multiple CAD imports"); imported=(ImportCadFileFeature)f;}
  }
  if(imported==null||model.getBodyManager().getBodies().size()!=1)throw new RuntimeException("Unexpected CAD structure");
  star.cadmodeler.Body oldBody=model.getBodyManager().getBodies().iterator().next();
  ModelReImportCommands cmd=imported.createModelReImportCommands();
  cmd.loadFileForReplaceBody(imported,output.resolve("HF_012_v3.x_t").toString());
  s.println("[NTNU] BODY_NAMES_0 "+cmd.getBodyNames(0));
  s.println("[NTNU] BODY_NAMES_1 "+cmd.getBodyNames(1));
  cmd.compareBodies(oldBody,"HF_012_v3");
  s.println("[NTNU] MATCHING_FACES "+cmd.getMatchingFaces(oldBody,"HF_012_v3"));
  if(!cmd.replaceBody(oldBody,"HF_012_v3",new ArrayList<Face>(),new Vector<String>()))throw new RuntimeException("CAD replace failed");
  if(!cmd.finalizeReplaceBody())throw new RuntimeException("CAD replacement finalization failed");
  model.update();
  model.updateParts();
  cad.setPresentationName("HF_012_v3");
  cad.getTessellationDensityOption().setSelected(TessellationDensityOption.Type.USER_DEFINED);
  TessellationParameters tp=cad.getTessellationDensityOption().getDetailedParameters();
  tp.setIsCurveChordTolerancePercentage(false);
  tp.setIsSurfacePlaneTolerancePercentage(false);
  tp.setCurveChordTolerance(1e-5);
  tp.setSurfacePlaneTolerance(1e-5);
  tp.setCurveChordAngle(0.5);
  tp.setSurfacePlaneAngle(0.5);
  cad.getTessellationDensityOption().setDetailedParameters(tp);
  cad.tessellate();
  cad.exportStlPart(output.resolve("star_012_verified_m.stl").toString(),false);
  SubtractPartsOperation subtract=(SubtractPartsOperation)s.get(MeshOperationManager.class).getObject("Subtract");
  subtract.execute();
  for(Boundary b:s.getRegionManager().getRegion("fluid").getBoundaryManager().getBoundaries())
   s.println("[NTNU] BOUNDARY "+b.getPresentationName()+" surfaces="+b.getPartSurfaceGroup());
  s.saveState(output.resolve("HF_012_baseline_unmeshed.sim").toString());
  s.println("[NTNU] CORRECTED_CAD_REIMPORTED_AND_BASELINE_SAVED");
 }
}