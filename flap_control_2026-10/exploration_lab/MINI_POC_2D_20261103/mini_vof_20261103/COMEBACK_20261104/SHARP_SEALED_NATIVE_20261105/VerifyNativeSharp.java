import java.util.*;
import java.nio.file.*;
import star.common.*;
import star.meshing.*;
import star.base.report.*;
import star.vis.*;

public class VerifyNativeSharp extends StarMacro {
  public void execute() {
    Simulation sim = getActiveSimulation();
    try { verify(sim, Paths.get(System.getenv("SHARP_NATIVE_DIR"))); }
    catch (Exception e) { throw new RuntimeException(e); }
  }
  private void verify(Simulation sim, Path dir) throws Exception {
    Region fluid = sim.getRegionManager().getRegions().iterator().next();
    AutoMeshOperation2d op = (AutoMeshOperation2d)sim.get(MeshOperationManager.class)
        .getObject("02 Sharp sealed native 2D mesh");
    FvRepresentation mesh = (FvRepresentation)sim.getRepresentationManager().getObject("Volume Mesh");
    long original = mesh.getCellCount();
    if (original != 7161 || sim.getSolution().getPhysicalTime()!=0.0 || !op.hasPrismMesher())
      throw new IllegalStateException("Unexpected saved state " + original);
    sim.println("VERIFIED_REOPEN_CELLS=" + original);
    double base = 0.06;
    op.getDefaultValues().get(BaseSize.class).setValue(base);
    op.execute();
    long count = mesh.getCellCount();
    if (count != 13467) throw new IllegalStateException("Unexpected repeat result " + count);
    save(sim, dir, fluid, mesh, original, count, base);
    double closer = 0.0475;
    op.getDefaultValues().get(BaseSize.class).setValue(closer);
    op.execute();
    count = mesh.getCellCount();
    if (count > 15000 && count < 20000) save(sim, dir, fluid, mesh, original, count, closer);
  }
  private void save(Simulation sim, Path dir, Region fluid, FvRepresentation mesh, long original, long count, double base) throws Exception {
    StringBuilder audit = new StringBuilder("reopened_cells="+original+"\ncells="+count+"\nbase_m="+base+"\n");
    for (String field : List.of("Volume","LeastSquaresQuality","FaceValidity")) {
      MinReport report = (MinReport)sim.getReportManager().getObject("Mesh minimum " + field);
      double v = report.getReportMonitorValue();
      if (!Double.isFinite(v) || v <= 0) throw new IllegalStateException("Invalid minimum " + field + " " + v);
      audit.append(field+"="+v+"\n");
    }
    String compact=mesh.generateCompactMeshReport(Collections.singletonList(fluid)).toString();
    for (String check : List.of("NumInvalidCells","NumUnclosedCells","NumNegVolCells","NumInvalidFaces"))
      if (!compact.contains("'"+check+"': 0")) throw new IllegalStateException("Invalid mesh: "+compact);
    audit.append("physical_time_s="+sim.getSolution().getPhysicalTime()+"\n"+compact+"\n");
    sim.saveState(dir.resolve("Sharp_Sealed_Native_2D_Comparable.sim").toString());
    Files.writeString(dir.resolve("FINAL_MESH_AUDIT.txt"),audit.toString());
    try {
      Scene scene = sim.getSceneManager().getScene("Sharp sealed - native 2D mesh");
      scene.printAndWait(dir.resolve("Sharp_Sealed_Native_Mesh_Final.png").toString(), 1, 1300, 760);
    } catch (Exception e) { sim.println("OPTIONAL_MESH_SCENE " + e); }
  }
}

