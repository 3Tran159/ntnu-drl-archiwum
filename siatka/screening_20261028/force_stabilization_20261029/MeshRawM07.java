package macro;
import star.common.*;import star.meshing.*;import star.sweptmesher.*;import star.prismmesher.*;import star.base.neo.*;import java.nio.file.*;import java.util.*;
public class MeshRawM07 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M07_build");
try{
Files.createDirectories(out);s.getSolution().clearSolutionWithoutMeshReset();
DirectedMeshOperation dm=(DirectedMeshOperation)s.get(MeshOperationManager.class).getObject("Q2D_directed");
DirectedAutoSourceMesh auto=(DirectedAutoSourceMesh)dm.getDirectedSurfaceMeshBaseManager().getObject("Q2D_polygon_prisms");
dm.editDirectedMeshOperation();double base=0.10204081632653061;
auto.getDefaultValues().get(BaseSize.class).setValue(base);
auto.getDefaultValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(0.00025510204081632655/base*100);
auto.getDefaultValues().get(PrismWallThickness.class).setValue(1.530612244897959e-06);
auto.getDefaultValues().get(NumPrismLayers.class).setNumLayers(48);
auto.getDefaultValues().get(PrismThickness.class).setRelativeSizeValue(.01546/base*100);
SurfaceCustomMeshControl foil=(SurfaceCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_foil_size");
foil.getCustomValues().get(PartsTargetSurfaceSize.class).setRelativeSize(0.0020408163265306124/base*100);
foil.getCustomValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(0.00020408163265306123/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_near_foil")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.006377551020408163/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_free_surface")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.020408163265306124/base*100);
for(DirectedMeshPartCollection pc:dm.getDirectedMeshPartCollectionManager().getObjects()){pc.setTargetSmoothOption(false);pc.setEnhanceCellQualityOption(false);}
long start=System.nanoTime();auto.updateAutoSourceMesh();dm.stopEditingDirectedMeshOperation();dm.execute();
double wall=(System.nanoTime()-start)*1e-9;
Files.writeString(out.resolve("mesh_timing.json"),"{\"mesh_time_s\":"+wall+",\"base_m\":"+base+",\"linear_refinement_ratio\":"+2.0+",\"prism_layers\":40,\"first_layer_m\":0.000003,\"total_prism_m\":0.01546}");
s.saveState(out.resolve("mesh_before_audit.sim").toString());
StarScript audit=new StarScript(s,Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/AuditRawM07.java").toFile());audit.play();if(audit.getInterruptedByException())throw new IllegalStateException("Mesh audit macro failed");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception x){}throw new RuntimeException(e);}
}}
