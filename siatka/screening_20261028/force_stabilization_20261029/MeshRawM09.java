package macro;
import star.common.*;import star.meshing.*;import star.sweptmesher.*;import star.prismmesher.*;import star.base.neo.*;import java.nio.file.*;import java.util.*;
public class MeshRawM09 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M09_build");
try{
Files.createDirectories(out);s.getSolution().clearSolutionWithoutMeshReset();
DirectedMeshOperation dm=(DirectedMeshOperation)s.get(MeshOperationManager.class).getObject("Q2D_directed");
DirectedAutoSourceMesh auto=(DirectedAutoSourceMesh)dm.getDirectedSurfaceMeshBaseManager().getObject("Q2D_polygon_prisms");
dm.editDirectedMeshOperation();double base=0.25;
auto.getDefaultValues().get(BaseSize.class).setValue(base);
auto.getDefaultValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(0.0003571428571428572/base*100);
auto.getDefaultValues().get(PrismWallThickness.class).setValue(1.530612244897959e-06);
auto.getDefaultValues().get(NumPrismLayers.class).setNumLayers(48);
auto.getDefaultValues().get(PrismThickness.class).setRelativeSizeValue(.01546/base*100);
SurfaceCustomMeshControl foil=(SurfaceCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_foil_size");
foil.getCustomValues().get(PartsTargetSurfaceSize.class).setRelativeSize(0.0028571428571428576/base*100);
foil.getCustomValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(0.00028571428571428574/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_near_foil")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.00892857142857143/base*100);
((VolumeCustomMeshControl)auto.getCustomMeshControls().getObject("Q2D_free_surface")).getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.028571428571428574/base*100);
SimpleBlockPart middle=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());
middle.setPresentationName("Q2D_protected_middle_M09");
middle.setCorners(new DoubleVector(new double[]{-11.9,-.1,-3}),new DoubleVector(new double[]{30.94,.1,3.2}));
middle.rebuildSimpleShapePart();
VolumeCustomMeshControl protection=auto.getCustomMeshControls().createVolumeControl();
protection.setPresentationName("Q2D_protected_middle_M09");protection.getGeometryObjects().setObjects(middle);
for(Object v:protection.getCustomConditions().getChildren())if(v instanceof VolumeControlBase)((VolumeControlBase)v).setVolumeControlBaseSizeOption(true);
protection.getCustomValues().get(VolumeControlSize.class).setRelativeSize(0.14285714285714288/base*100);
for(DirectedMeshPartCollection pc:dm.getDirectedMeshPartCollectionManager().getObjects()){pc.setTargetSmoothOption(false);pc.setEnhanceCellQualityOption(false);}
long start=System.nanoTime();auto.updateAutoSourceMesh();dm.stopEditingDirectedMeshOperation();dm.execute();
double wall=(System.nanoTime()-start)*1e-9;
Files.writeString(out.resolve("mesh_timing.json"),"{\"mesh_time_s\":"+wall+",\"base_m\":"+base+",\"linear_refinement_ratio\":"+2.0+",\"prism_layers\":48,\"first_layer_m\":1.530612244897959e-06,\"total_prism_m\":0.01546}");
s.saveState(out.resolve("mesh_before_audit.sim").toString());
StarScript audit=new StarScript(s,Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/AuditRawM09.java").toFile());audit.play();if(audit.getInterruptedByException())throw new IllegalStateException("Mesh audit macro failed");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception x){}throw new RuntimeException(e);}
}}
