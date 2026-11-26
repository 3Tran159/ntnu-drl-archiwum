import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.base.report.*;
import star.common.*;
import star.flow.*;
import star.post.*;
import star.vis.*;

public class AfLiveOutput extends StarMacro {
  Simulation s;
  Path out;
  Region region;
  List<Boundary> walls = new ArrayList<>(), flap = new ArrayList<>();
  Map<String,ReportMonitor> monitors = new LinkedHashMap<>();
  final double hx=.952, hy=.02128173276777;
  public void execute() {
    s=getActiveSimulation();
    try {
      out=Paths.get(System.getenv("AF_LIVE_OUT"));
      region=s.getRegionManager().getRegions().iterator().next();
      long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
      double begin=s.getSolution().getPhysicalTime();
      if (cells!=17462 || begin<.523 || s.getNumberOfGpgpus()!=0 ||
          !s.getFieldFunctionManager().hasFunction("VolumeFractionwater")) throw new IllegalStateException("Unexpected live VOF identity");
      for(Boundary b:region.getBoundaryManager().getBoundaries()) {
        String n=b.getPresentationName().toLowerCase(Locale.ROOT);
        if(n.contains("main")||n.contains("flap")) walls.add(b);
        if(n.contains("flap")) flap.add(b);
      }
      if(walls.size()!=2||flap.size()!=1)throw new IllegalStateException("Unexpected foil boundaries");
      boolean moving=s.getFieldFunctionManager().hasFunction("AF_Cycle_Command");
      reports(moving);
      SolutionHistory h=history();
      long deadline=System.nanoTime()+30_000_000_000L;
      while(monitors.get("AF_CL").getAllYValues().length==0 && System.nanoTime()<deadline)
        Thread.sleep(1000);
      StringBuilder receipt=new StringBuilder("start="+begin+"\n");
      for(var m:monitors.entrySet()) {
        double[] y=m.getValue().getAllYValues();
        receipt.append(m.getKey()+" n="+y.length+" last="+(y.length==0?"-":y[y.length-1])+"\n");
      }
      receipt.append("time_s="+s.getSolution().getPhysicalTime()+"\n");
      receipt.append("states="+h.getNumberOfStates()+"\n");
      s.saveState(out.resolve("VOF_AF_Instrumented.sim").toString());
      Files.writeString(out.resolve("AF_READBACK.txt"),receipt.toString());
    }catch(Exception e){throw new RuntimeException(e);}
  }
  FieldFunction ff(String n){return s.getFieldFunctionManager().getFunction(n);}
  ReportMonitor watch(Report r,String name) {
    r.setPresentationName(name);
    ReportMonitor m=r.createMonitor();
    m.setPresentationName(name+" Monitor");
    m.getStarUpdate().setUpdateMode(StarUpdate.TIMESTEP);
    m.getStarUpdate().setUpdateFrequency(1);
    monitors.put(name,m);
    return m;
  }
  ExpressionReport expr(String name,String formula,Dimensions dim){
    ExpressionReport r=s.getReportManager().createReport(ExpressionReport.class);
    if(dim!=null)r.setDimensions(dim);
    r.setDefinition(formula);
    watch(r,name);
    return r;
  }
  void plot(String title,ReportMonitor x,String... keys) {
    List<Monitor> list=new ArrayList<>();
    for(String k:keys)list.add(monitors.get(k));
    MonitorPlot p=s.getPlotManager().createMonitorPlot(list,title);
    p.setPresentationName(title);
    p.setTitle(title);
    p.setXAxisMonitor(x);
  }
  void reports(boolean moving){
    for(int axis=0;axis<2;axis++){
      ForceReport f=s.getReportManager().createReport(ForceReport.class);
      f.getDirection().setComponents(axis==0?1:0,axis==1?1:0,0);
      f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);
      f.getParts().setObjects(walls);
      watch(f,axis==0?"AF_Fx":"AF_Fz");
    }
    MomentReport mh=s.getReportManager().createReport(MomentReport.class);
    mh.getDirection().setComponents(0,0,-1);mh.getOrigin().setComponents(hx,hy,.01);
    mh.setPressureOption(FluidLoadsReportPressureOption.SP_UC);mh.getParts().setObjects(flap);
    watch(mh,"AF_Mh");
    UserFieldFunction unity=s.getFieldFunctionManager().createFieldFunction();
    unity.setFunctionName("AF_UnitVolume");unity.setDefinition("1");
    VolumeIntegralReport volume=s.getReportManager().createReport(VolumeIntegralReport.class);
    volume.setFieldFunction(unity);volume.getParts().setObjects(region);volume.setPresentationName("AF_FluidVolume");
    expr("AF_CL","(${AF_FzReport}-<9810 N/m^3>*(<11.2 m^3>-${AF_FluidVolumeReport}))/<3855.6 N>",null);
    expr("AF_CD","${AF_FxReport}/<3855.6 N>",null);
    MinReport pressure=s.getReportManager().createReport(MinReport.class);
    pressure.getParts().setObjects(flap);pressure.setSmooth(false);pressure.setFieldFunction(ff("AbsolutePressure"));
    watch(pressure,"AF_Flap_pAbs_Min");
    Dimensions time=new Dimensions();time.setTime(1);
    expr("AF_Time","$Time",time);
    expr("AF_Delta_Command_deg",moving?"$AF_Cycle_Command":"0",null);
    expr("AF_Delta_Measured_deg","0",null);
    ReportMonitor x=monitors.get("AF_Time");
    plot("AF 01 - Lift coefficient vs time",x,"AF_CL");
    plot("AF 02 - Drag coefficient vs time",x,"AF_CD");
    plot("AF 03 - Foil forces vs time [N]",x,"AF_Fx","AF_Fz");
    plot("AF 04 - Hinge moment vs time [N m]",x,"AF_Mh");
    plot("AF 05 - Flap deflection vs time [deg]",x,"AF_Delta_Command_deg","AF_Delta_Measured_deg");
    plot("AF 06 - Flap minimum absolute pressure vs time",x,"AF_Flap_pAbs_Min");
    if(!Double.isFinite(monitors.get("AF_CL").getReport().getReportMonitorValue())||
       !Double.isFinite(monitors.get("AF_CD").getReport().getReportMonitorValue())) throw new IllegalStateException("Invalid AF coefficient expression");
  }
  DoubleVector v(double x,double y,double z){return new DoubleVector(new double[]{x,y,z});}
  Scene scene(String name, Representation rep, double halfHeight) {
    Scene sc=s.getSceneManager().createScene(name);
    sc.setPresentationName(name);
    sc.initializeAndWait();
    PartDisplayer outline=sc.getDisplayerManager().createPartDisplayer("Main foil and flap");
    outline.getInputParts().setObjects(walls);outline.setRepresentation(rep);outline.setOutline(true);
    sc.getCurrentView().setInput(v(.6,.05,.01),v(.6,.05,3),v(0,1,0),halfHeight,1,
       s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
    return sc;
  }
  SolutionHistory history(){
    Path path=out.resolve("VOF_AF_Live.simh");
    if(Files.exists(path))throw new IllegalStateException("AF history exists");
    PlaneSection plane=s.getPartManager().createPlaneSection();
    plane.setPresentationName("AF live - Midspan section");
    plane.getInputParts().setObjects(region);plane.setOrigin(v(0,0,.01));plane.setOrientation(v(0,0,1));
    SolutionHistory h=s.get(SolutionHistoryManager.class).createForFile(path.toString(),false);
    h.setPresentationName("AF - Live VOF Solution History");
    h.setAutoRecord(false);h.setAutoRescan(true);
    h.getRegions().setObjects(region);
    List<NamedObject> input=new ArrayList<>(walls);input.add(plane);
    h.getInputs().setObjects(input);
    h.setFunctions(List.of(ff("AbsolutePressure"),ff("Velocity"),ff("Velocity").getMagnitudeFunction(),ff("VolumeFractionwater")));
    h.createSnapshot("AF_live_attachment");
    RecordedSolutionView view=h.createRecordedSolutionView();
    view.setPresentationName("AF - Live VOF playback");view.setStateIndex(h.getMinStateIndex());
    Representation rep=view.getRepresentation();
    scene("AF VOF 01 - Recorded foil geometry",rep,.36);
    scalar("AF VOF 02 - Recorded absolute pressure",rep,plane,ff("AbsolutePressure"),.36);
    scalar("AF VOF 03 - Recorded speed",rep,plane,ff("Velocity").getMagnitudeFunction(),.36);
    Scene sc=scene("AF VOF 04 - Recorded streamlines",rep,.51);
    StreamPart lines=s.getPartManager().createStreamPart();lines.setPresentationName("AF live - Upstream streamline seeds");
    lines.getInputParts().setObjects(region);lines.setFieldFunction(ff("Velocity"));lines.setMode(SeedMode.LINE);
    lines.getLineSeed().setPoint1(v(-.38,-.38,.01));lines.getLineSeed().setPoint2(v(-.38,.42,.01));lines.getLineSeed().setResolution(51);
    StreamDisplayer sd=sc.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
    sd.getInputParts().setObjects(lines);sd.setRepresentation(rep);sd.setMode(StreamDisplayerMode.LINES);
    sd.setColorMode(StreamColorMode.SCALAR);sd.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
    scalar("AF VOF 05 - Recorded water volume fraction",rep,plane,ff("VolumeFractionwater"),2.6);
    StarUpdate u=h.getStarUpdateStageable().getStarUpdate();
    u.setUpdateMode(StarUpdate.TIMESTEP);u.setUpdateFrequency(25);
    h.setAutoRecord(true);
    return h;
  }
  void scalar(String name,Representation rep,PlaneSection plane,FieldFunction f,double halfHeight) {
    Scene sc=scene(name,rep,halfHeight);
    ScalarDisplayer sd=sc.getDisplayerManager().createScalarDisplayer(f.getPresentationName());
    sd.getInputParts().setObjects(plane);sd.setRepresentation(rep);sd.getScalarDisplayQuantity().setFieldFunction(f);
  }
}

