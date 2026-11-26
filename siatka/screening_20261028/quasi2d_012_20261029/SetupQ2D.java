package macro;
import star.common.*;
import star.meshing.*;
import star.sweptmesher.*;
import star.prismmesher.*;
import star.base.neo.*;
import star.base.report.*;
import star.vis.*;
import java.nio.file.*;
import java.util.*;
public class SetupQ2D extends StarMacro {
public void execute(){
Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029");
try{
s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
Set<GeometryPart> before=new HashSet<>(s.getGeometryPartManager().getParts());
s.get(PartImportManager.class).importCadPart(root.resolve("HF_012_constant_section.x_t").toString(),"SharpEdges",30,4,1e-8);
CadPart foil=null;for(GeometryPart p:s.getGeometryPartManager().getParts())if(!before.contains(p)&&p instanceof CadPart)foil=(CadPart)p;
if(foil==null)throw new RuntimeException("Foil import missing");
foil.setPresentationName("Q2D_foil");
foil.getTessellationDensityOption().setSelected(TessellationDensityOption.Type.USER_DEFINED);
TessellationParameters tp=foil.getTessellationDensityOption().getDetailedParameters();
tp.setIsCurveChordTolerancePercentage(false);tp.setIsSurfacePlaneTolerancePercentage(false);tp.setCurveChordTolerance(1e-5);tp.setSurfacePlaneTolerance(1e-5);tp.setCurveChordAngle(.5);tp.setSurfacePlaneAngle(.5);foil.getTessellationDensityOption().setDetailedParameters(tp);foil.tessellate();
SimpleBlockPart block=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());block.setPresentationName("Q2D_domain");
block.setCorners(new DoubleVector(new double[]{-11.9,.01,-22}),new DoubleVector(new double[]{30.94,.03,8}));block.rebuildSimpleShapePart();
PartSurface all=block.getPartSurfaceManager().getPartSurfaces().iterator().next();
block.splitPartSurfaceByPatch(all,List.of(block.getMinXFace()),"inlet",s);
block.splitPartSurfaceByPatch(all,List.of(block.getMaxXFace()),"outlet",s);
block.splitPartSurfaceByPatch(all,List.of(block.getMinYFace()),"span_source",s);
block.splitPartSurfaceByPatch(all,List.of(block.getMaxYFace()),"span_target",s);
block.splitPartSurfaceByPatch(all,List.of(block.getMinZFace()),"bottom",s);all.setPresentationName("top");
MeshOperationManager mom=s.get(MeshOperationManager.class);
SubtractPartsOperation sub=(SubtractPartsOperation)mom.createSubtractPartsOperation(List.of(block,foil));sub.setPresentationName("Q2D_fluid");sub.setTargetPart(block);sub.execute();
MeshOperationPart part=(MeshOperationPart)s.getGeometryPartManager().getPart("Q2D_fluid");
part.exportStlPart(root.resolve("q2d_boolean_m.stl").toString(),false);
Region reg=s.getRegionManager().getRegion("fluid");
reg.getPartGroup().setObjects(part);
for(Boundary b:reg.getBoundaryManager().getBoundaries())b.getPartSurfaceGroup().setObjects(new ArrayList<PartSurface>());
List<PartSurface> walls=new ArrayList<>();PartSurface src=null,tgt=null;
for(PartSurface p:part.getPartSurfaces()){
 String n=p.getPresentationName();s.println("[Q2D] surface "+n);
 if(n.contains("Q2D_foil")){walls.add(p);continue;}
 String key=n.substring(n.lastIndexOf('.')+1);
 if(key.equals("span_source")){src=p;Boundary b=reg.getBoundaryManager().createEmptyBoundary();b.setPresentationName("Q2D_span_source");b.setBoundaryType(SymmetryBoundary.class);b.getPartSurfaceGroup().setObjects(p);}
 else if(key.equals("span_target")){tgt=p;Boundary b=reg.getBoundaryManager().createEmptyBoundary();b.setPresentationName("Q2D_span_target");b.setBoundaryType(SymmetryBoundary.class);b.getPartSurfaceGroup().setObjects(p);}
 else {Boundary b;try{b=reg.getBoundaryManager().getBoundary("DOMAIN."+key);}catch(Exception e){b=reg.getBoundaryManager().createEmptyBoundary();b.setPresentationName("DOMAIN."+key);}b.getPartSurfaceGroup().setObjects(p);if(key.equals("bottom"))b.setBoundaryType(SymmetryBoundary.class);}
}
if(src==null||tgt==null||walls.isEmpty())throw new RuntimeException("Boundary identification failed");
Boundary wall=reg.getBoundaryManager().getBoundary("HF_v2 2.ColoredFace1");wall.setPresentationName("HF_012_wall");wall.getPartSurfaceGroup().setObjects(walls);
DirectedMeshOperation dm=(DirectedMeshOperation)mom.createDirectedMeshOperation(List.of(part));dm.setPresentationName("Q2D_directed");
dm.getSourceSurfaceGroup().setObjects(src);dm.getTargetSurfaceGroup().setObjects(tgt);
boolean editing=dm.editDirectedMeshOperation();s.println("[Q2D] editing="+editing);
List<DirectedMeshPartCollection> pcs=new ArrayList<>(dm.getDirectedMeshPartCollectionManager().getObjects());
s.println("[Q2D] collections="+pcs);
if(pcs.isEmpty())throw new RuntimeException("No directed part collections");
DirectedAutoSourceMesh auto=dm.getDirectedSurfaceMeshBaseManager().createAutoSourceMesh(List.of("star.twodmesher.DualAutoMesher2d","star.prismmesher.PrismAutoMesher"),pcs);
auto.setPresentationName("Q2D_polygon_prisms");
auto.getDefaultValues().get(BaseSize.class).setValue(.4);
auto.getDefaultValues().get(NumPrismLayers.class).setNumLayers(15);
auto.getDefaultValues().get(PrismThickness.class).setRelativeSizeValue(.01546/.4*100);
DirectedMeshDistribution dist=dm.getDirectedMeshDistributionManager().createDirectedMeshDistribution(pcs);
dist.getDefaultValues().get(DirectedMeshNumLayers.class).setNumLayers(1);
s.println("[Q2D] defaults="+auto.getDefaultValues().getChildren());
s.println("[Q2D] distribution="+dist.getDefaultValues().getChildren());
dm.stopEditingDirectedMeshOperation();
s.saveState(root.resolve("Q2D_configured.sim").toString());
Files.writeString(root.resolve("setup_done.json"),"{\"status\":\"configured\",\"span_m\":0.02,\"sweep_layers\":1}");
}catch(Exception e){try{Files.writeString(root.resolve("setup_error.txt"),e.toString());}catch(Exception x){}throw new RuntimeException(e);}
}}
