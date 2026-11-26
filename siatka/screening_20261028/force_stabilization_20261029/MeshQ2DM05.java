package macro;
import star.common.*;import star.meshing.*;import star.sweptmesher.*;import star.prismmesher.*;import star.base.neo.*;import java.nio.file.*;import java.util.*;
public class MeshQ2DM05 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M05");
try{
Files.createDirectories(out);s.getSolution().clearSolutionWithoutMeshReset();
DirectedMeshOperation dm=(DirectedMeshOperation)s.get(MeshOperationManager.class).getObject("Q2D_directed");
DirectedAutoSourceMesh auto=(DirectedAutoSourceMesh)dm.getDirectedSurfaceMeshBaseManager().getObject("Q2D_polygon_prisms");
dm.editDirectedMeshOperation();double base=.4/2.5;
auto.getDefaultValues().get(BaseSize.class).setValue(base);
auto.getDefaultValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(.0005/base*100);
auto.getDefaultValues().get(PrismWallThickness.class).setValue(0.0001799);
auto.getDefaultValues().get(NumPrismLayers.class).setNumLayers(15);
auto.getDefaultValues().get(PrismThickness.class).setRelativeSizeValue(.01546/base*100);
SurfaceCustomMeshControl foil=(SurfaceCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_foil_size");
foil.getCustomValues().get(PartsTargetSurfaceSize.class).setRelativeSize(.008/2.5/base*100);
foil.getCustomValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(.0008/2.5/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_near_foil")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(.025/2.5/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_free_surface")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(.08/2.5/base*100);
for(DirectedMeshPartCollection pc:dm.getDirectedMeshPartCollectionManager().getObjects()){pc.setTargetSmoothOption(false);pc.setEnhanceCellQualityOption(false);}
long start=System.nanoTime();auto.updateAutoSourceMesh();dm.stopEditingDirectedMeshOperation();dm.execute();
double wall=(System.nanoTime()-start)*1e-9;
Files.writeString(out.resolve("mesh_timing.json"),"{\"mesh_time_s\":"+wall+",\"base_m\":"+base+",\"linear_refinement_ratio\":"+2.5+",\"prism_layers\":15,\"first_layer_m\":0.0001799,\"total_prism_m\":0.01546}");
s.saveState(out.resolve("mesh_before_audit.sim").toString());
StarScript audit=new StarScript(s,Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/AuditQ2DM05.java").toFile());audit.play();if(audit.getInterruptedByException())throw new IllegalStateException("Audit failed");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception x){}throw new RuntimeException(e);}
}}
