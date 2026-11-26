package macro;
import star.common.*;import star.sweptmesher.*;import star.meshing.*;import java.nio.file.*;import java.util.*;
public class FixSweep extends StarMacro {
public void execute(){
Simulation s=getActiveSimulation();DirectedMeshOperation dm=(DirectedMeshOperation)s.get(MeshOperationManager.class).getObject("Q2D_directed");
dm.editDirectedMeshOperation();
for(DirectedMeshPartCollection pc:dm.getDirectedMeshPartCollectionManager().getObjects()){s.println("[Q2D] TargetSmooth was "+pc.getTargetSmoothOption()+" enhanced "+pc.getEnhanceCellQualityOption());pc.setTargetSmoothOption(false);pc.setEnhanceCellQualityOption(false);}
dm.stopEditingDirectedMeshOperation();long t=System.nanoTime();dm.execute();s.println("[Q2D] Sweep_no_smoothing_wall_s="+(System.nanoTime()-t)*1e-9);
s.saveState("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M01/mesh_after_sweep_fix.sim");
}}
