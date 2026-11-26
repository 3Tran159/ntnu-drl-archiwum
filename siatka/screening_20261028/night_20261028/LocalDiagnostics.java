package macro;
import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.vis.*;
import java.nio.file.*;
import java.util.*;

/** Diagnostic exports only; never saves or iterates the source simulation. */
public class LocalDiagnostics extends StarMacro {
  private Simulation s; private Path out; private FvRepresentation fv; private Region fluid;
  public void execute(){s=getActiveSimulation();try{
    Path source=Paths.get(System.getenv("NTNU_DIAG_SOURCE")).toAbsolutePath().normalize();
    out=Paths.get(System.getenv("NTNU_DIAG_OUTPUT")).toAbsolutePath().normalize();
    if(!source.startsWith(Paths.get("F:/ntnu/mesh_screening_20261028"))||!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(source)||Files.exists(out))throw new IllegalStateException("Source/output guard");
    if(s.getSimulationIterator().getAutoSave().getEnabled()||s.getSimulationIterator().getAutoSave().getAutoSaveBatch())throw new IllegalStateException("Autosave enabled");
    int iter=s.getSimulationIterator().getCurrentIteration();Files.createDirectories(out);
    fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");fluid=s.getRegionManager().getRegion("fluid");
    StringBuilder metrics=new StringBuilder("field,comparison,threshold,count\n");
    for(double cut:new double[]{80,85})threshold(metrics,"SkewnessAngle",cut,true);
    for(double cut:new double[]{0.01,0.001,0.00001})threshold(metrics,"VolumeChange",cut,false);
    for(double cut:new double[]{0.01,0.001,0.00001})threshold(metrics,"CellQuality",cut,false);
    Files.writeString(out.resolve("threshold_counts.csv"),metrics);
    for(double y:new double[]{0.5,2.75,4.2503873,5.4}){
      PlaneSection plane=s.getPartManager().createPlaneSection();plane.setPresentationName("NTNU_section_y_"+y);
      plane.getInputParts().setObjects(fluid);plane.setOrigin(new DoubleVector(new double[]{0,y,0}));plane.setOrientation(new DoubleVector(new double[]{0,1,0}));
      Scene scene=s.getSceneManager().createScene("NTNU_mesh_section_"+y);
      PartDisplayer mesh=scene.getDisplayerManager().createPartDisplayer("Mesh");mesh.setRepresentation(fv);mesh.getInputParts().setObjects(plane);mesh.setSurface(false);mesh.setOutline(false);mesh.setMesh(true);
      scene.initializeAndWait();
      // Camera looks along +y; x horizontal and z vertical, parallel projection.
      double chordEnd=y<=2.75?1.19:1.19-(y-2.75)*(1.19-0.6)/(5.5-2.75);
      double leading=y<=2.75?0:(y-2.75)*0.24/(5.5-2.75);
      shot(scene,y,(leading+chordEnd)/2,0,0.15,"whole");
      shot(scene,y,leading,0,0.035,"leading");
      shot(scene,y,chordEnd,0,0.035,"trailing");
      if(y>4.2&&y<4.3)shot(scene,y,0.12092684,-0.01364575,0.008,"worst_quality");
      s.getSceneManager().remove(scene);
      s.println("[NTNU] SECTION_DONE y="+y);
    }
    if(s.getSimulationIterator().getCurrentIteration()!=iter)throw new IllegalStateException("Unexpected solver iteration");
    Files.writeString(out.resolve("DONE.txt"),"Diagnostic exports completed; source not saved; no solver iterations.\n");
  }catch(Exception e){throw new RuntimeException(e);}}
  private void shot(Scene scene,double y,double x,double z,double halfHeight,String tag){
    CurrentView view=scene.getCurrentView();view.setFocalPoint(new DoubleVector(new double[]{x,y,z}));view.setPosition(new DoubleVector(new double[]{x,y-2,z}));view.setViewUp(new DoubleVector(new double[]{0,0,1}));view.setProjectionModeToParallel();view.setParallelScale(halfHeight);
    scene.printAndWait(out.resolve("section_y"+y+"_"+tag+".png").toString(),1,1800,900);
  }
  private void threshold(StringBuilder result,String name,double cut,boolean above){
    FieldFunction f=s.getFieldFunctionManager().getFunction(name);ThresholdPart p=s.getPartManager().createThresholdPart();p.setPresentationName("NTNU_"+name+"_"+cut);p.getInputParts().setObjects(fluid);p.setFieldFunction(f);p.setRange(new DoubleVector(new double[]{cut,cut}));p.setMode(above?ThresholdMode.ABOVE_TAG:ThresholdMode.BELOW_TAG);
    ElementCountReport count=s.getReportManager().createReport(ElementCountReport.class);count.getParts().setObjects(p);count.setRepresentation(fv);double n=count.getReportMonitorValue();if(!Double.isFinite(n)||!count.getErrorLog().isBlank())throw new IllegalStateException("Threshold failed");
    result.append(name+","+(above?">":"<")+","+cut+","+n+"\n");
    if(n>0&&n<100000){XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(p);List<FieldFunction> fs=new ArrayList<>();for(String k:List.of("CellQuality","SkewnessAngle","VolumeChange","PrismLayerNumber","PrismCellThickness"))fs.add(s.getFieldFunctionManager().getFunction(k));table.setFieldFunctions(fs);table.setRepresentation(fv);table.setExtractVertexData(false);table.extract();table.export(out.resolve(name+"_"+cut+".csv").toString());}
  }
}
