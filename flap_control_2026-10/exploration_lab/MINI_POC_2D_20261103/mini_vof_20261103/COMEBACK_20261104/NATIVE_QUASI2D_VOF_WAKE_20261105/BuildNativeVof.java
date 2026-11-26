import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.base.report.*;
import star.common.*;
import star.meshing.*;
import star.post.*;
import star.prismmesher.*;
import star.resurfacer.*;
import star.sweptmesher.*;
import star.vis.*;
import star.vof.*;

public class BuildNativeVof extends StarMacro {
  Simulation s;
  Path out;
  Units m;
  final double base=.65;

  public void execute(){
    s=getActiveSimulation();
    out=Paths.get(System.getenv("NATIVE_VOF_DIR"));
    try { build(); }
    catch(Exception e){
      try{Files.writeString(out.resolve("NATIVE_ERROR.txt"),e.toString());}catch(Exception ignored){}
      throw new RuntimeException(e);
    }
  }

  void build() throws Exception{
    Region region=s.getRegionManager().getRegions().iterator().next();
    FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
    double time=s.getSolution().getPhysicalTime();
    if(Math.abs(time-.723)>1e-8||fv.getCellCount()!=17462||s.getNumberOfGpgpus()!=0||
       region.getPhysicsContinuum().getModelManager().hasModel(SegregatedVofModel.class)==null)
       throw new IllegalStateException("Paused VOF checkpoint identity failed");
    m=s.getUnitsManager().getObject("m");
    s.getSimulationIterator().getAutoSave().setEnabled(false);
    for(SolutionHistory h:s.get(SolutionHistoryManager.class).getObjects()){
      h.setAutoRecord(false);
      h.setAutoRescan(false);
    }
    SimulationPartManager pm=s.get(SimulationPartManager.class);
    Set<GeometryPart> before=new HashSet<>(pm.getLeafParts());
    s.get(PartImportManager.class).importStlPart(out.resolve("SharpSealedFluidDomain.stl").toString(),
         "OneSurfacePerPatch",m,true,1e-8);
    List<GeometryPart> added=new ArrayList<>(pm.getLeafParts());
    added.removeAll(before);
    if(added.size()!=1)throw new IllegalStateException("Expected one new geometry part");
    GeometryPart domain=added.get(0);
    domain.setPresentationName("Sharp sealed fluid domain - 20 mm span");
    Map<String,PartSurface> surfaces=new LinkedHashMap<>();
    for(PartSurface p:domain.getPartSurfaces())surfaces.put(p.getPresentationName(),p);
    Map<String,String> links=Map.of("main","Main","flap","Flap","inlet","Inlet","outlet","Outlet",
                                   "bottom","Bottom","top","Top","span_front","Span0","span_back","Span1");
    Map<String,Boundary> boundaries=new LinkedHashMap<>();
    for(Boundary b:region.getBoundaryManager().getBoundaries())boundaries.put(b.getPresentationName().toLowerCase(Locale.ROOT),b);
    if(!surfaces.keySet().equals(new HashSet<>(links.values()))||!boundaries.keySet().equals(links.keySet()))
      throw new IllegalStateException("Geometry/boundary identity mismatch: "+surfaces.keySet()+" / "+boundaries.keySet());
    s.getSolution().clearSolution(Solution.Clear.Fields,Solution.Clear.History);
    region.getPartGroup().setObjects(List.of(domain));
    for(var link:links.entrySet())
      boundaries.get(link.getKey()).getPartSurfaceGroup().setObjects(surfaces.get(link.getValue()));
    s.println("NATIVE_BOUNDARIES="+boundaries.keySet());

    MeshOperationManager operations=s.get(MeshOperationManager.class);
    DirectedMeshOperation mesh=(DirectedMeshOperation)operations.createDirectedMeshOperation(List.of(domain));
    mesh.setPresentationName("01 Native VOF mesh - one span layer");
    mesh.getSourceSurfaceGroup().setObjects(surfaces.get("Span0"));
    mesh.getTargetSurfaceGroup().setObjects(surfaces.get("Span1"));
    mesh.editDirectedMeshOperation();
    List<DirectedMeshPartCollection> collections=new ArrayList<>(mesh.getDirectedMeshPartCollectionManager().getObjects());
    if(collections.size()!=1)throw new IllegalStateException("Expected one sweep collection");
    for(DirectedMeshPartCollection c:collections){c.setTargetSmoothOption(false);c.setEnhanceCellQualityOption(false);}
    DirectedAutoSourceMesh a=mesh.getDirectedSurfaceMeshBaseManager().createAutoSourceMesh(
        List.of("star.twodmesher.DualAutoMesher2d","star.prismmesher.PrismAutoMesher"),collections);
    a.setPresentationName("Polygonal source - foil prisms, wake and free surface");
    a.getDefaultValues().get(BaseSize.class).setValue(base);
    a.getDefaultValues().get(PartsTargetSurfaceSize.class).setRelativeSize(100);
    a.getDefaultValues().get(PartsMinimumSurfaceSize.class).setAbsoluteSize(.004,m);
    a.getDefaultValues().get(SurfaceGrowthRate.class).setGrowthRate(1.25);
    a.getDefaultValues().get(NumPrismLayers.class).setNumLayers(3);
    a.getDefaultValues().get(PrismThickness.class).setAbsoluteSize(.000643032,m);
    a.getDefaultValues().get(PrismLayerStretching.class).setStretching(1.18);

    List<PartSurface> skin=List.of(surfaces.get("Main"),surfaces.get("Flap"));
    SurfaceCustomMeshControl foil=surface(a,"Foil wall size - 9 mm",skin);
    foil.getCustomConditions().get(PartsTargetSurfaceSizeOption.class).setSelected(PartsTargetSurfaceSizeOption.Type.CUSTOM);
    foil.getCustomConditions().get(PartsMinimumSurfaceSizeOption.class).setSelected(PartsMinimumSurfaceSizeOption.Type.CUSTOM);
    foil.getCustomValues().get(PartsTargetSurfaceSize.class).setAbsoluteSize(.009,m);
    foil.getCustomValues().get(PartsMinimumSurfaceSize.class).setAbsoluteSize(.001,m);
    List<PartSurface> outer=new ArrayList<>(surfaces.values());outer.removeAll(skin);
    SurfaceCustomMeshControl far=surface(a,"No boundary prism layers outside foil",outer);
    far.getCustomConditions().get(PartsCustomizePrismMesh.class).getCustomPrismOptions()
       .setSelected(PartsCustomPrismsOption.Type.DISABLE);
    volume(a,"Foil neighbourhood - 25 mm",new double[]{-.30,-.33,-.01},new double[]{1.48,.39,.03},.025);
    volume(a,"Free surface band - 55 mm",new double[]{-10.5,1.65,-.01},new double[]{26.5,2.40,.03},.055);

    SurfaceCustomMeshControl wake=surface(a,"Wake Refinement - flap to downstream",List.of(surfaces.get("Flap")));
    boolean wakeEnabled=false;
    List<String> wakeKeys=new ArrayList<>();
    for(Object v:wake.getCustomConditions().getChildren()){
      wakeKeys.add(v.getClass().getName());
      if(v instanceof PartsRemesherTetPolyWakeRefinementOption w){
        w.setPartsWakeRefinementOption(true);wakeEnabled=w.getPartsWakeRefinementOption();
      }else if(v instanceof PartsWakeRefinementOption w){
        w.setPartsWakeRefinementOption(true);wakeEnabled=w.getPartsWakeRefinementOption();
      }
    }
    s.println("NATIVE_WAKE_OPTIONS="+wakeKeys);
    if(!wakeEnabled)throw new IllegalStateException("Native Wake Refinement not available in this source mesh "+wakeKeys);
    PartsWakeRefinementValuesManager w=wake.getCustomValues().get(PartsWakeRefinementValuesManager.class);
    w.getRelativeOrAbsoluteOption().setSelected(RelativeOrAbsoluteOption.Type.ABSOLUTE);
    w.getDirection().setComponents(1,0,0);
    w.getDistance().setValue(1.6);
    w.getSpreadAngle().setUnits(s.getUnitsManager().getObject("deg"));
    w.getSpreadAngle().setValue(6);
    w.getIsotropicSize().setAbsoluteSize(.04,m);
    s.println("NATIVE_WAKE enabled=true length_m="+w.getDistance().getSIValue()+" angle_deg="+w.getSpreadAngle().getValue());
    DirectedMeshDistribution distribution=mesh.getDirectedMeshDistributionManager().createDirectedMeshDistribution(collections);
    distribution.getDefaultValues().get(DirectedMeshNumLayers.class).setNumLayers(1);
    a.updateAutoSourceMesh();
    mesh.stopEditingDirectedMeshOperation();
    mesh.execute();

    List<Region> regions=List.of(region);
    int orient=s.get(MeshManager.class).checkFaceOrientation(regions);
    if(orient>0)s.get(MeshManager.class).repairFaceOrientation(regions);
    int after=s.get(MeshManager.class).checkFaceOrientation(regions);
    long count=fv.getCellCount();
    NeoProperty report=fv.generateMeshReport(regions);
    double minVol=metric("Volume",region,true);
    double minQ=metric("CellQuality",region,true);
    double minF=metric("FaceValidity",region,true);
    double zMin=metric("Position",region,true),zMax=metric("Position",region,false);
    double front=metric("Position",boundaries.get("span_front"),true);
    double back=metric("Position",boundaries.get("span_back"),false);
    Files.writeString(out.resolve("MESH_AUDIT.txt"),report.toFormattedString()+"\ncells="+count+
      "\norientation_before="+orient+"\norientation_after="+after+
      "\nmin_volume_m3="+minVol+"\nmin_cell_quality="+minQ+"\nmin_face_validity="+minF+
      "\nspan_m="+(back-front)+"\ncentroid_z_min="+zMin+"\ncentroid_z_max="+zMax+
      "\nphysical_time_s="+s.getSolution().getPhysicalTime()+"\nwake_native="+wakeEnabled+"\n");
    if(!report.getBoolean("success")||count<=0||count>55000||after!=0||!(minVol>0&&minQ>0&&minF>.5)
       ||Math.abs(zMin-.01)>1e-7||Math.abs(zMax-.01)>1e-7||Math.abs((back-front)-.02)>1e-7)
       throw new IllegalStateException("Native mesh integrity or span gate failed");
    XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);
    t.setPresentationName("Native mesh cell diagnostics");
    t.getParts().setObjects(region);
    t.setRepresentation(fv);
    t.setFieldFunctions(List.of(ff("Volume"),ff("CellQuality"),ff("FaceValidity")));
    t.extract();t.export(out.resolve("MESH_CELLS.csv").toString(),",");
    XyzInternalTable edges=s.getTableManager().createTable(XyzInternalTable.class);
    edges.setPresentationName("Native outer boundary face diagnostics");
    edges.getParts().setObjects(List.of(boundaries.get("inlet"),boundaries.get("outlet"),boundaries.get("top"),boundaries.get("bottom")));
    edges.setRepresentation(fv);
    edges.setFieldFunctions(List.of(ff("Area").getMagnitudeFunction()));
    edges.extract();edges.export(out.resolve("OUTER_FACES.csv").toString(),",");
    s.saveState(out.resolve("Sharp_Sealed_VOF_Native_Quasi2D.sim").toString());
    try{
      scene("Mesh 01 - Full domain and free-surface band",boundaries.get("span_front"),fv,8,-3,9);
      scene("Mesh 02 - Hydrofoil and wake refinement",boundaries.get("span_front"),fv,1.05,.12,1.42);
      s.saveState(out.resolve("Sharp_Sealed_VOF_Native_Quasi2D.sim").toString());
    }catch(Exception e){s.println("OPTIONAL SCENE "+e);}
  }
  FieldFunction ff(String name){return s.getFieldFunctionManager().getFunction(name);}
  double metric(String name,NamedObject part,boolean minimum){
    AnalysisReport q=minimum?s.getReportManager().createReport(MinReport.class):s.getReportManager().createReport(MaxReport.class);
    FieldFunction f=ff(name);
    FieldFunction selected=name.equals("Position")?f.getComponentFunction(2):f;
    if(q instanceof MinReport low)low.setFieldFunction(selected);else ((MaxReport)q).setFieldFunction(selected);
    q.getParts().setObjects(part);q.setSmooth(false);
    return q.getReportMonitorValue();
  }
  SurfaceCustomMeshControl surface(DirectedAutoSourceMesh a,String name,List<PartSurface> faces){
    SurfaceCustomMeshControl c=a.getCustomMeshControls().createSurfaceControl();
    c.setPresentationName(name);c.getGeometryObjects().setObjects(faces);return c;
  }
  void volume(DirectedAutoSourceMesh a,String name,double[] lo,double[] hi,double size){
    SimpleBlockPart p=s.get(MeshPartFactory.class).createNewBlockPart(s.getGeometryPartManager());
    p.setPresentationName(name);p.setCorners(new DoubleVector(lo),new DoubleVector(hi));p.rebuildSimpleShapePart();
    VolumeCustomMeshControl c=a.getCustomMeshControls().createVolumeControl();
    c.setPresentationName(name);c.getGeometryObjects().setObjects(p);
    for(Object v:c.getCustomConditions().getChildren())
      if(v instanceof VolumeControlBase setting)setting.setVolumeControlBaseSizeOption(true);
    c.getCustomValues().get(VolumeControlSize.class).setRelativeSize(size/base*100);
  }
  DoubleVector v(double x,double y,double z){return new DoubleVector(new double[]{x,y,z});}
  void scene(String name,Boundary cap,FvRepresentation fv,double x,double y,double scale){
    Scene sc=s.getSceneManager().createScene(name);sc.setPresentationName(name);sc.initializeAndWait();
    PartDisplayer pd=sc.getDisplayerManager().createPartDisplayer("Span face and mesh");
    pd.getInputParts().setObjects(cap);pd.setRepresentation(fv);pd.setMesh(true);pd.setOutline(true);
    sc.getCurrentView().setInput(v(x,y,0),v(x,y,5),v(0,1,0),scale,1,
      s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
    sc.printAndWait(out.resolve(name.startsWith("Mesh 01")?"NATIVE_VOF_DOMAIN.png":"NATIVE_VOF_FOIL_WAKE.png").toString(),1,1440,810);
  }
}

