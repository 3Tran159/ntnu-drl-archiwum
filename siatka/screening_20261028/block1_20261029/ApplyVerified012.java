package macro;
import star.common.*;
import star.meshing.*;
import java.nio.file.*;
public class ApplyVerified012 extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path audit=Paths.get("F:/ntnu/mesh_screening_20261028/block1_20261029");
  Path output=Paths.get("F:/ntnu/geometry_012_20261029");
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(audit.resolve("source_copy.sim").toAbsolutePath().normalize()))throw new RuntimeException("Wrong source");
  s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  s.getSimulationIterator().getAutoSave().setEnabled(false);
  CadPart cad=(CadPart)s.getGeometryPartManager().getPart("HF_v2");
  cad.reimportPart2(output.resolve("HF_012_v3.x_t").toString(),1e-8);
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
  s.saveState(output.resolve("HF_012_baseline_unmeshed.sim").toString());
  s.println("[NTNU] CORRECTED_CAD_REIMPORTED_AND_BASELINE_SAVED");
 }
}