package macro;
import star.common.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.meshing.*;import star.trimmer.*;import star.material.*;import star.flow.*;import star.segregatedflow.*;import star.motion.*;import star.vis.*;import java.nio.file.*;import java.util.*;
public class BuildFlapPOC extends StarMacro {
 Simulation s;Path out=Paths.get("C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_poc_2606_20261102");double xh,zh;Units meters;
 void note(String t)throws Exception{s.println("POC_STAGE "+t);Files.writeString(out.resolve("audit/build_progress.txt"),t+"\n");}
 double number(String text,String key){java.util.regex.Matcher m=java.util.regex.Pattern.compile("\""+key+"\"\\s*:\\s*([-+0-9.eE]+)").matcher(text);if(!m.find())throw new IllegalStateException(key);return Double.parseDouble(m.group(1));}
 MeshPart load(String name)throws Exception{
  Set<GeometryPart> before=new HashSet<>(s.getGeometryPartManager().getLeafParts());
  s.get(PartImportManager.class).importStlPart(out.resolve("geometry/"+name+".stl").toString(),"OneSurfacePerPatch",meters,true,1e-7);
  for(GeometryPart p:s.getGeometryPartManager().getLeafParts())if(!before.contains(p)){p.setPresentationName(name);return (MeshPart)p;}
  throw new IllegalStateException("Import failed "+name);
 }
 SimpleBlockPart box(String name,double[] a,double[] b){
  SimpleBlockPart p=s.get(MeshPartFactory.class).createNewBlockPart(s.get(SimulationPartManager.class));p.setPresentationName(name);p.setCorners(new DoubleVector(a),new DoubleVector(b));p.rebuildSimpleShapePart();
  p.getPartSurfaceManager().splitPartSurfacesByAngle(new ArrayList<>(p.getPartSurfaces()),89);
  return p;
 }
 MeshOperationPart subtract(MeshPart a,MeshPart b,String name){
  SubtractPartsOperation sub=(SubtractPartsOperation)s.get(MeshOperationManager.class).createSubtractPartsOperation(Arrays.asList(a,b));sub.setPresentationName(name+"_Boolean");sub.setTargetPart(a);sub.setPerformCADBoolean(false);sub.execute();
  MeshOperationPart p=(MeshOperationPart)sub.getOutputParts().getObjects().iterator().next();p.setPresentationName(name);return p;
 }
 Region region(GeometryPart p,String name){
  Set<Region> before=new HashSet<>(s.getRegionManager().getRegions());
  s.getRegionManager().newRegionsFromParts(Arrays.asList(p),"OneRegion",null,"OneBoundaryPerPartSurface",null,RegionManager.CreateInterfaceMode.BOUNDARY);
  for(Region r:s.getRegionManager().getRegions())if(!before.contains(r)){r.setPresentationName(name);return r;}throw new IllegalStateException(name);
 }
 AutoMeshOperation mesh(GeometryPart p,String name,double size){
  AutoMeshOperation m=s.get(MeshOperationManager.class).createAutoMeshOperation(Arrays.asList("star.resurfacer.ResurfacerAutoMesher","star.trimmer.TrimmerAutoMesher"),Arrays.asList(p));
  m.setPresentationName(name);m.getDefaultValues().get(BaseSize.class).setValue(size);
  m.getDefaultValues().get(PartsTargetSurfaceSize.class).setRelativeSize(100);
  m.getDefaultValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(30);
  return m;
 }
 FieldFunction component(int j){return s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j);}
 double bound(Boundary b,int j,boolean min){
  ScalarReport r=min?s.getReportManager().createReport(MinReport.class):s.getReportManager().createReport(MaxReport.class);
  r.setFieldFunction(component(j));r.getParts().setObjects(b);double v=r.getReportMonitorValue();s.getReportManager().removeObjects(r);return v;
 }
 ForceReport force(String name,double[] dir,List<Boundary> walls){
  ForceReport r=s.getReportManager().createReport(ForceReport.class);r.setPresentationName(name);r.getDirection().setComponents(dir[0],dir[1],dir[2]);r.getParts().setObjects(walls);return r;
 }
 public void execute(){
  s=getActiveSimulation();
  try{
   if(!"native_profile_poc_2606".equals(System.getenv("NTNU_FLAP_POC_BUILD"))||!s.getRegionManager().getRegions().isEmpty())throw new IllegalStateException("Owned empty POC simulation required");
   if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only PoC");
   String cfg=Files.readString(out.resolve("geometry/geometry.json"));xh=number(cfg,"hinge_x_m");zh=number(cfg,"hinge_z_m");
   meters=s.getUnitsManager().getObject("m");
   note("importing rounded native-profile parts");
   MeshPart main=load("POC_Main"),flap=load("POC_Flap");
   SimpleBlockPart outer=box("POC_Domain",new double[]{-1.2,-.01,-1.2},new double[]{3.6,.01,1.2});
   SimpleBlockPart inner=box("POC_Cage",new double[]{xh-.22,-.01,zh-.28},new double[]{1.55,.01,zh+.28});
   MeshOperationPart bgp=subtract(outer,main,"POC_Background"),ovp=subtract(inner,flap,"POC_Overset");
   Region bg=region(bgp,"Background"),ov=region(ovp,"FlapOverset");
   PhysicsContinuum pc=s.getContinuumManager().createContinuum(PhysicsContinuum.class);pc.setPresentationName("POC water calm laminar");
   pc.enable(ThreeDimensionalModel.class);pc.enable(ImplicitUnsteadyModel.class);pc.enable(SingleComponentLiquidModel.class);pc.enable(SegregatedFlowModel.class);pc.enable(ConstantDensityModel.class);pc.enable(LaminarModel.class);
   Material water=pc.getModelManager().getModel(SingleComponentLiquidModel.class).getMaterial();
   water.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).setConstant(1000);
   water.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).setConstant(.001);
   bg.setPhysicsContinuum(pc);ov.setPhysicsContinuum(pc);
   pc.getInitialConditions().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(1,0,0);
   AutoMeshOperation bm=mesh(bgp,"Coarse background",.08),om=mesh(ovp,"Coarse overset",.012);
   SimpleBlockPart refine=box("POC_Refinement",new double[]{-.15,-.03,-.38},new double[]{1.7,.03,.42});
   VolumeCustomMeshControl control=bm.getCustomMeshControls().createVolumeControl();control.getGeometryObjects().setObjects(refine);control.getCustomConditions().get(VolumeControlTrimmerSizeOption.class).setVolumeSourceTrimmerSizeOption(true);control.getCustomValues().get(VolumeControlSize.class).setRelativeSize(15);
   note("meshing coarse background");bm.execute();note("meshing coarse overset");om.execute();
   long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
   Files.writeString(out.resolve("audit/cell_count.txt"),Long.toString(cells));
   if(cells>90000)throw new IllegalStateException("PoC cell cap exceeded: "+cells);
   note("assigning boundaries from coordinates");
   List<Boundary> walls=new ArrayList<>();List<Boundary> flapwalls=new ArrayList<>();
   StringBuilder audit=new StringBuilder("cells="+cells+"\n");
   for(Region r:Arrays.asList(bg,ov))for(Boundary b:r.getBoundaryManager().getBoundaries()){
    double ax=bound(b,0,true),bx=bound(b,0,false),ay=bound(b,1,true),by=bound(b,1,false),az=bound(b,2,true),bz=bound(b,2,false);
    String kind;
    if(Math.abs(by-ay)<1e-7){b.setBoundaryType(SymmetryBoundary.class);kind="span";}
    else if(r==bg&&Math.abs(ax+1.2)<1e-7&&Math.abs(bx+1.2)<1e-7){b.setBoundaryType(InletBoundary.class);b.getValues().get(VelocityMagnitudeProfile.class).getMethod(ConstantScalarProfileMethod.class).getQuantity().setValue(1);kind="inlet";}
    else if(r==bg&&Math.abs(ax-3.6)<1e-7&&Math.abs(bx-3.6)<1e-7){b.setBoundaryType(PressureBoundary.class);kind="outlet";}
    else if(r==bg&&Math.abs(bz-az)<1e-7&&(Math.abs(az-1.2)<1e-7||Math.abs(az+1.2)<1e-7)){b.setBoundaryType(SymmetryBoundary.class);kind="farfield";}
    else if(r==ov&&((Math.abs(bx-ax)<1e-7&&(Math.abs(ax-(xh-.22))<1e-7||Math.abs(ax-1.55)<1e-7))||(Math.abs(bz-az)<1e-7&&(Math.abs(az-(zh-.28))<1e-7||Math.abs(az-(zh+.28))<1e-7)))){b.setBoundaryType(OversetMeshBoundary.class);kind="overset";}
    else{b.setBoundaryType(WallBoundary.class);walls.add(b);if(r==ov)flapwalls.add(b);kind=r==ov?"flap":"main";}
    audit.append(r.getPresentationName()+"."+b.getPresentationName()+" "+kind+" bounds="+Arrays.toString(new double[]{ax,bx,ay,by,az,bz})+"\n");
   }
   if(flapwalls.isEmpty()||walls.size()<=flapwalls.size())throw new IllegalStateException("Wall identification failed");
   Files.writeString(out.resolve("audit/boundaries.txt"),audit.toString());
   IndirectRegionInterface inter=s.getInterfaceManager().createIndirectRegionInterface(bg,ov,"Flap overset connectivity");inter.setInterfaceType(OversetMeshInterface.class);inter.setUseAlternateHoleCutting(true);inter.setEnabledZeroDonorCheck(true);
   RotatingMotion rot=s.get(MotionManager.class).createMotion(RotatingMotion.class,"Flap sinusoidal +/-5deg");
   rot.getAxisOrigin().setComponents(xh,0,zh);rot.getAxisDirection().setComponents(0,1,0);rot.getRotationSpecificationOption().setSelected(RotationSpecificationOption.Type.RotationAngle);
   ((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition("<5 deg>*sin(2*3.141592653589793*$Time/<0.2 s>)");
   ov.getValues().get(MotionSpecification.class).setMotion(rot);
   force("POC Fx total N",new double[]{1,0,0},walls);force("POC Fz total N",new double[]{0,0,1},walls);
   MomentReport mh=s.getReportManager().createReport(MomentReport.class);mh.setPresentationName("POC Mh flap Nm");mh.getDirection().setComponents(0,1,0);mh.getOrigin().setComponents(xh,0,zh);mh.getParts().setObjects(flapwalls);
   for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())c.setIsUsed(false);
   ImplicitUnsteadySolver u=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);u.getTimeStep().setValue(.002);
   for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(8);}
   
   note("saving coarse motion-ready case");s.saveState(out.resolve("FlapPOC_2606_mesh_ready.sim").toString());
   Files.writeString(out.resolve("audit/build_complete.txt"),"Coarse native foil + rounded flap; x/c=.80; +/-5 deg; CPU; U=1m/s; no transient steps yet.\n");
  }catch(Exception e){try{Files.writeString(out.resolve("audit/build_error.txt"),e.toString());s.saveState(out.resolve("FlapPOC_2606_build_error.sim").toString());}catch(Exception ignore){}throw new RuntimeException(e);}
 }
}
