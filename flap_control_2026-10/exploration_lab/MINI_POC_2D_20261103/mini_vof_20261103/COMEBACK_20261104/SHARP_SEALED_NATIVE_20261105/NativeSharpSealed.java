import java.util.*;
import java.nio.file.*;
import star.common.*;
import star.meshing.*;
import star.prismmesher.*;
import star.base.report.*;
import star.flow.*;
import star.kwturb.*;
import star.turbulence.*;
import star.vis.*;
import star.base.neo.DoubleVector;

public class NativeSharpSealed extends StarMacro {
  public void execute() {
    Simulation sim = getActiveSimulation();
    try { build(sim, Paths.get(System.getenv("SHARP_NATIVE_DIR"))); }
    catch (Exception e) { throw new RuntimeException(e); }
  }

  private void build(Simulation sim, Path dir) throws Exception {
    RegionManager regions = sim.getRegionManager();
    Region old = regions.getObjects().iterator().next();
    PhysicsContinuum physics = old.getPhysicsContinuum();
    Units metres = sim.getUnitsManager().getObject("m");
    sim.get(PartImportManager.class).importStlPart(dir.resolve("SharpSealedFluidDomain.stl").toString(),
        "OneSurfacePerPatch", metres, true, 1e-8);
    Collection<GeometryPart> parts = sim.get(SimulationPartManager.class).getLeafParts();
    if (parts.size() != 1) throw new IllegalStateException("Expected one geometry part, got " + parts.size());
    GeometryPart part = parts.iterator().next();
    part.setPresentationName("Sharp sealed fluid domain");
    for (PartSurface face : part.getPartSurfaces()) sim.println("NATIVE_INPUT " + face.getPresentationName());

    MeshOperationManager operations = sim.get(MeshOperationManager.class);
    MeshOperation prepare = operations.createPrepareFor2dOperation(Collections.singletonList(part));
    prepare.setPresentationName("01 Prepare sharp sealed for 2D");
    prepare.execute();
    regions.removeRegions(Collections.singletonList(old));
    regions.newRegionsFromParts(Collections.singletonList(part), "OneRegion", null,
        "OneBoundaryPerPartSurface", null, RegionManager.CreateInterfaceMode.BOUNDARY);
    Region fluid = regions.getObjects().iterator().next();
    fluid.setPhysicsContinuum(physics);
    fluid.setPresentationName("Sharp sealed water");
    for (Boundary b : fluid.getBoundaryManager().getBoundaries()) {
      String name = b.getPresentationName();
      if (name.endsWith("Inlet")) {
        b.setBoundaryType(InletBoundary.class);
        b.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);
        b.getValues().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(18,0,0);
        b.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
        b.getValues().get(TurbulentKineticEnergyProfile.class).getMethod(ConstantScalarProfileMethod.class).getQuantity().setValue(0.000486);
        b.getValues().get(SpecificDissipationRateProfile.class).getMethod(ConstantScalarProfileMethod.class).getQuantity().setValue(48.6);
      }
      else if (name.endsWith("Outlet")) b.setBoundaryType(PressureBoundary.class);
      else if (name.endsWith("Top") || name.endsWith("Bottom")) b.setBoundaryType(SymmetryBoundary.class);
      sim.println("NATIVE_BOUNDARY " + name + " " + b.getBoundaryType().getClass().getSimpleName());
    }
    AutoMeshOperation2d mesh = operations.createAutoMeshOperation2d(
        Arrays.asList("star.twodmesher.DualAutoMesher2d","star.prismmesher.PrismAutoMesher"),
        Collections.singletonList(part));
    mesh.setPresentationName("02 Sharp sealed native 2D mesh");
    double base = Double.parseDouble(System.getenv("SHARP_BASE_M"));
    mesh.getDefaultValues().get(BaseSize.class).setValue(base);
    mesh.getDefaultValues().get(PartsTargetSurfaceSize.class).setRelativeSize(100);
    mesh.getDefaultValues().get(PartsMinimumSurfaceSize.class).setRelativeSize(3);
    mesh.getDefaultValues().get(NumPrismLayers.class).setNumLayers(3);
    mesh.getDefaultValues().get(PrismThickness.class).setAbsoluteSize(0.000643032, metres);
    mesh.getDefaultValues().get(PrismLayerStretching.class).setStretching(1.18);
    sim.println("NATIVE_2D_MESHERS " + operations.getCore2dMeshers());
    sim.println("NATIVE_MESH_DEFAULTS " + mesh.getDefaultValues().getObjects());
    List<PartSurface> foil = new ArrayList<>();
    for (PartSurface face : part.getPartSurfaces()) {
      String name = face.getPresentationName();
      if (name.endsWith("Main") || name.endsWith("Flap")) foil.add(face);
    }
    if (foil.size()!=2) throw new IllegalStateException("Missing main foil or flap part surface");
    SurfaceCustomMeshControl wallSize = mesh.getCustomMeshControls().createSurfaceControl();
    wallSize.setPresentationName("Foil and flap surface size");
    wallSize.getGeometryObjects().setObjects(foil);
    wallSize.getCustomConditions().get(PartsTargetSurfaceSizeOption.class).setSelected(PartsTargetSurfaceSizeOption.Type.CUSTOM);
    wallSize.getCustomConditions().get(PartsMinimumSurfaceSizeOption.class).setSelected(PartsMinimumSurfaceSizeOption.Type.CUSTOM);
    wallSize.getCustomValues().get(PartsTargetSurfaceSize.class).setAbsoluteSize(0.009, metres);
    wallSize.getCustomValues().get(PartsMinimumSurfaceSize.class).setAbsoluteSize(0.001, metres);
    sim.saveState(dir.resolve("Sharp_Sealed_Native_SETUP.sim").toString());
    mesh.execute();
    FvRepresentation volume = (FvRepresentation) sim.getRepresentationManager().getObject("Volume Mesh");
    long count = volume.getCellCount();
    if (count == 0) throw new IllegalStateException("No native cells");
    if (count < 14000 || count > 21000) {
      double newBase = base * Math.sqrt((double)count/17462);
      mesh.getDefaultValues().get(BaseSize.class).setValue(newBase);
      sim.println("NATIVE_BASE_TUNE=" + newBase + " original cell count " + count);
      mesh.execute();
      count = volume.getCellCount();
      base = newBase;
    }
    sim.println("NATIVE_CELLS=" + count);
    StringBuilder audit = new StringBuilder("cells="+count+"\nbase_m="+base+"\n");
    for (String field : List.of("Volume","LeastSquaresQuality","FaceValidity")) {
      MinReport report = sim.getReportManager().createReport(MinReport.class);
      report.setPresentationName("Mesh minimum " + field);
      report.setFieldFunction(sim.getFieldFunctionManager().getFunction(field));
      report.getParts().setObjects(fluid);
      double v = report.getReportMonitorValue();
      if (!Double.isFinite(v) || v <= 0) throw new IllegalStateException("Invalid minimum " + field + " " + v);
      audit.append(field+"="+v+"\n");
    }
    audit.append("physical_time_s="+sim.getSolution().getPhysicalTime()+"\n");
    sim.println("NATIVE_COMPACT_REPORT " + volume.generateCompactMeshReport(Collections.singletonList(fluid)));
    Files.writeString(dir.resolve("NATIVE_MESH_AUDIT.txt"),audit.toString());
    sim.saveState(dir.resolve("Sharp_Sealed_Native_2D.sim").toString());
    try {
      Scene scene = sim.getSceneManager().createScene("Sharp sealed - native 2D mesh");
      scene.initializeAndWait();
      PartDisplayer cells = scene.getDisplayerManager().createPartDisplayer("Native cells");
      cells.getInputParts().setObjects(fluid);
      cells.setRepresentation(volume);
      cells.setMesh(true);
      cells.setOutline(true);
      scene.getCurrentView().setInput(
          new DoubleVector(new double[]{0.60,0,0}), new DoubleVector(new double[]{0.60,0,3}),
          new DoubleVector(new double[]{0,1,0}), 0.52, 1,
          sim.getCoordinateSystemManager().getLabCoordinateSystem(), false);
      scene.printAndWait(dir.resolve("Sharp_Sealed_Native_Mesh.png").toString(), 1, 1300, 760);
      sim.saveState(dir.resolve("Sharp_Sealed_Native_2D.sim").toString());
    } catch (Exception e) {
      sim.println("OPTIONAL_MESH_SCENE " + e);
    }
  }
}

