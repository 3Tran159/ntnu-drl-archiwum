package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.post.*;
import java.nio.file.*;import java.util.*;
public class CampaignFoilWave extends StarMacro {
 private Simulation s;private Path out;private Region reg;private FvRepresentation fv;
 private double domainXmin,domainXmax,requestedLambda;
 private boolean stopRequested()throws Exception{
  if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL")))return true;
  Path p=out.resolve("manual_stop_at_time.txt");if(Files.exists(p)){double t=Double.parseDouble(Files.readString(p).trim());if(!Double.isFinite(t)||t<0)throw new IllegalStateException("Invalid stop schedule");if(s.getSolution().getPhysicalTime()>=t-1e-9)return true;}
  Path q=out.resolve("manual_stop_at_epoch.txt");if(Files.exists(q)&&System.currentTimeMillis()/1000.0>=Double.parseDouble(Files.readString(q).trim()))return true;
  return false;
 }
 private String json(Object o){
  if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Map.Entry<?,?> e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
  if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Iterable<?>)o)j.add(json(a));return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
 private MaxReport max(String name,FieldFunction ff,NamedObject part){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setPresentationName(name);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(part);r.createMonitor();return r;}
 private SurfaceIntegralReport integral(PlaneSection p,FieldFunction ff){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(p);r.setSmooth(false);return r;}

 private Continuum phase(PhysicsContinuum pc,String name)throws Exception{
  for(Object model:pc.getModelManager().getChildren()){
   try{
    Object pm=model.getClass().getMethod("getPhaseManager").invoke(model);
    Object ph=pm.getClass().getMethod("getPhase",String.class).invoke(pm,name);
    if(ph instanceof Continuum)return (Continuum)ph;
   }catch(NoSuchMethodException ignored){}
  }
  throw new IllegalStateException("Required Eulerian phase not found: "+name);
 }
 private MassConservationErrorReport nativeError(String name,Continuum phase){
  MassConservationErrorReport r=s.getReportManager().createReport(MassConservationErrorReport.class);
  r.setPresentationName(name);r.setPhase(phase);r.setRepresentation(fv);r.setSmooth(false);r.getParts().setObjects(reg);
  r.setUnits((Units)s.getUnitsManager().getObject("kg"));
  if(!r.getPhase().equals(phase))throw new IllegalStateException("Native phase report binding mismatch");
  return r;
 }
 private Object getter(Object o,String method){
  try{Object value=o.getClass().getMethod(method).invoke(o);return value==null?null:value.toString();}
  catch(Exception ex){return "UNAVAILABLE:"+ex.getClass().getSimpleName();}
 }
 private Map<String,Object> nativeDefinition(MassConservationErrorReport r){
  Map<String,Object>d=new LinkedHashMap<>();d.put("name",r.getPresentationName());d.put("phase",r.getPhase().getPresentationName());
  d.put("units",r.getUnits().toString());d.put("representation",String.valueOf(r.getRepresentation()));d.put("parts",r.getParts().getObjects().toString());d.put("smooth",r.getSmooth());
  d.put("meaning","Native phase transport mass imbalance summed over cells and multiplied by the physical time step; kg per step. Independent iteration-error diagnostic, not a replacement for the inventory-plus-boundary-flux diagnostic.");
  return d;
 }

 private SumReport cellSum(String fieldName){
  SumReport r=s.getReportManager().createReport(SumReport.class);r.setPresentationName("Inspect_CellSum_"+fieldName);r.setRepresentation(fv);r.setSmooth(false);r.setFieldFunction(s.getFieldFunctionManager().getFunction(fieldName));r.getParts().setObjects(reg);return r;
 }
 private void localSnapshot(double t,double nativeWaterKgS,double nativeAirKgS,SumReport sw,SumReport sa,SumReport sm)throws Exception{
  double w=sw.getReportMonitorValue(),a=sa.getReportMonitorValue(),m=sm.getReportMonitorValue();
  boolean calibrated=Double.isFinite(w)&&Double.isFinite(a)&&Math.abs(w-nativeWaterKgS)<1e-7*Math.max(1,Math.abs(nativeWaterKgS))&&Math.abs(a-nativeAirKgS)<1e-7*Math.max(1,Math.abs(nativeAirKgS));
  Map<String,Object>d=new LinkedHashMap<>();d.put("time_s",t);d.put("native_water_kg_s",nativeWaterKgS);d.put("native_air_kg_s",nativeAirKgS);d.put("cell_sum_water",w);d.put("cell_sum_air",a);d.put("cell_sum_mixture",m);d.put("water_units",String.valueOf(sw.getUnits()));d.put("air_units",String.valueOf(sa.getUnits()));d.put("smooth",false);d.put("calibrated_as_native_decomposition",calibrated);d.put("note","Unsmoothed cell sum without volume multiplication. Interpret as native phase error decomposition ONLY if calibration passes. Spatial diagnostics do not establish clipping.");
  String tag=String.format(Locale.ROOT,"local_balance_t%.3f",t);Files.writeString(out.resolve(tag+".json"),json(d));
  XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(reg);tab.setRepresentation(fv);tab.setExtractVertexData(false);
  ArrayList<FieldFunction> fields=new ArrayList<>();for(String name:List.of("MassImbalancewater","MassImbalanceair","MassImbalance","VolumeFractionwater","Density","Pressure","CourantNumber"))fields.add(s.getFieldFunctionManager().getFunction(name));
  FieldFunction v=s.getFieldFunctionManager().getFunction("Velocity");fields.add(v.getComponentFunction(0));fields.add(v.getComponentFunction(1));fields.add(v.getComponentFunction(2));fields.add(v.getMagnitudeFunction());tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(tag+".csv").toString());
 }
 private ReportMonitor everyInner(MassConservationErrorReport r){
  ReportMonitor mon=r.createMonitor();mon.setEnabled(true);StarUpdate u=mon.getStarUpdate();u.setEnabled(true);u.getUpdateModeOption().setSelected(StarUpdateModeOption.Type.ITERATION);
  u.getIterationUpdateFrequency().setIterationFrequencyDefinition("1");u.getIterationUpdateFrequency().setStartIterationDefinition("0");u.getIterationUpdateFrequency().setStopEnabled(false);
  if(!String.valueOf(u.getUpdateModeOption().getSelectedElement()).equals("ITERATION"))throw new IllegalStateException("Native monitor notperiteration");
  return mon;
 }
 private ThresholdPart outletCells;
 private ArrayList<Scene> inspectionScenes=new ArrayList<>();
 private ForceReport fx,fz,fp,fvForce;
 private ReportMonitor zoneWaterMonitor,zoneAirMonitor;
 private FieldFunction ff(String name){return s.getFieldFunctionManager().getFunction(name);}
 private ThresholdPart threshold(String name,NamedObject input,FieldFunction field,double lo,double hi){
  ThresholdPart p=s.getPartManager().createThresholdPart();p.setPresentationName(name);p.getInputParts().setObjects(input);p.setFieldFunction(field);p.setRange(new DoubleVector(new double[]{lo,hi}));p.setMode(ThresholdMode.BETWEEN_TAG);return p;
 }
 private ForceReport force(String name,ForceReportForceOption.Type type,double x,double z){
  ForceReport r=s.getReportManager().createReport(ForceReport.class);r.setPresentationName(name);r.setRepresentation(fv);r.getParts().setObjects(reg.getBoundaryManager().getBoundary("HF_012_wall"));r.getForceOption().setSelected(type);r.getDirection().setComponents(x,0,z);return r;
 }
 private ReportMonitor innerMonitor(Report r){
  ReportMonitor m=r.createMonitor();m.setEnabled(true);StarUpdate u=m.getStarUpdate();u.setEnabled(true);u.getUpdateModeOption().setSelected(StarUpdateModeOption.Type.ITERATION);u.getIterationUpdateFrequency().setIterationFrequencyDefinition("1");return m;
 }
 private void setupForces(){
  fx=force("Inspect Drag total [N, slice]",ForceReportForceOption.Type.PRESSURE_AND_SHEAR,1,0);
  fz=force("Inspect Lift total [N, slice]",ForceReportForceOption.Type.PRESSURE_AND_SHEAR,0,1);
  fp=force("Inspect Drag pressure [N, slice]",ForceReportForceOption.Type.PRESSURE,1,0);
  fvForce=force("Inspect Drag viscous [N, slice]",ForceReportForceOption.Type.SHEAR,1,0);
  s.getPlotManager().createMonitorPlot(List.of(fx.createMonitor(),fz.createMonitor(),fp.createMonitor(),fvForce.createMonitor()),"Inspect - Foil forces (slice N)");
 }
 private double[] forces(){
  double a=fx.getReportMonitorValue(),b=fz.getReportMonitorValue(),p=fp.getReportMonitorValue(),v=fvForce.getReportMonitorValue();
  for(double x:new double[]{a,b,p,v})if(!Double.isFinite(x))throw new IllegalStateException("Nonfinite independent foil force");
  if(Math.abs(a-p-v)>1e-6*Math.max(1,Math.abs(a)))throw new IllegalStateException("Force component sum mismatch");
  return new double[]{a,b,p,v};
 }
 private Scene scalarScene(String name,NamedObject part,FieldFunction field,double xc,double zc,double scale,boolean cell,double lo,double hi){
  Scene sc=s.getSceneManager().createScene("Inspect "+name);
  if(part instanceof StreamPart){StreamDisplayer d=sc.getDisplayerManager().createStreamDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(part);d.getScalarDisplayQuantity().setFieldFunction(field);d.getScalarDisplayQuantity().setAutoRange(false);d.getScalarDisplayQuantity().setRange(new DoubleVector(new double[]{lo,hi}));}
  else{ScalarDisplayer d=sc.getDisplayerManager().createScalarDisplayer(name);d.setRepresentation(fv);d.getInputParts().setObjects(part);d.getScalarDisplayQuantity().setFieldFunction(field);
  if(Double.isFinite(lo)&&Double.isFinite(hi)){d.getScalarDisplayQuantity().setAutoRange(false);d.getScalarDisplayQuantity().setRange(new DoubleVector(new double[]{lo,hi}));}else d.getScalarDisplayQuantity().setAutoRange(true);
  if(cell)d.setFillMode(ScalarFillMode.CELL_FILLED_MESH);}
  PartDisplayer wall=sc.getDisplayerManager().createPartDisplayer("Foil outline");wall.setRepresentation(fv);wall.getInputParts().setObjects(reg.getBoundaryManager().getBoundary("HF_012_wall"));wall.setSurface(true);wall.setOutline(true);
  CurrentView cv=sc.getCurrentView();cv.setProjectionMode(VisProjectionMode.PARALLEL);cv.setFocalPoint(new DoubleVector(new double[]{xc,.02,zc}));cv.setPosition(new DoubleVector(new double[]{xc,-100,zc}));cv.setViewUp(new DoubleVector(new double[]{0,0,1}));cv.setParallelScale(scale);
  inspectionScenes.add(sc);return sc;
 }
 private StreamPart streams(String name,double x,double z1,double z2,int n){
  StreamPart st=s.getPartManager().createStreamPart();st.setPresentationName(name);st.getInputParts().setObjects(reg);st.setFieldFunction(ff("Velocity"));st.setMode(StreamPart.LINESEED);st.getLineSeed().setPoint1(new DoubleVector(new double[]{x,.02,z1}));st.getLineSeed().setPoint2(new DoubleVector(new double[]{x,.02,z2}));st.getLineSeed().setResolution(n);st.getIntegrator().setDirection(StreamPart.BOTH);st.getIntegrator().setMaxPropagation(90);st.getIntegrator().setMaximumNumberOfSteps(1500);return st;
 }
 private void setupViews()throws Exception{
  PlaneSection mid=s.getPartManager().createPlaneSection();mid.setPresentationName("Inspect mid-span x-z inspection plane");mid.getInputParts().setObjects(reg);mid.setOrigin(new DoubleVector(new double[]{0,.02,0}));mid.setOrientation(new DoubleVector(new double[]{0,1,0}));
  outletCells=threshold("Inspect last two outlet columns",reg,ff("Position").getComponentFunction(0),domainXmax-.4,domainXmax+.000001);
  IsoPart fs=s.getPartManager().createIsoPart();fs.setPresentationName("Inspect water surface alpha = 0.5");fs.getInputParts().setObjects(reg);fs.setFieldFunction(ff("VolumeFractionwater"));fs.setMode(IsoPart.SINGLE);fs.getSingleIsoValue().setValue(.5);
  scalarScene("01 Whole tank - water fraction",mid,ff("VolumeFractionwater"),5,-7,23,false,0,1);
  scalarScene("02 Free surface alpha 0.5 - elevation",fs,ff("Position").getComponentFunction(2),5,2,23,false,1.5,2.5);
  scalarScene("03 Foil - pressure Pa",mid,ff("Pressure"),.7,0,1.2,false,Double.NaN,Double.NaN);
  scalarScene("04 Foil - speed m per s",mid,ff("Velocity").getMagnitudeFunction(),.7,0,1.2,false,0,30);
  scalarScene("05 Foil - instantaneous streamlines",streams("Inspect streamlines near foil",-1,-.8,.8,45),ff("Velocity").getMagnitudeFunction(),.7,0,1.2,false,0,30);
  scalarScene("06 Outlet - water fraction and cells",mid,ff("VolumeFractionwater"),domainXmax-.6,2,.8,true,0,1);
  scalarScene("07 Outlet - water mass imbalance kg per s",mid,ff("MassImbalancewater"),domainXmax-.6,2,.8,true,Double.NaN,Double.NaN);
  scalarScene("08 Outlet - air mass imbalance kg per s",mid,ff("MassImbalanceair"),domainXmax-.6,2,.8,true,Double.NaN,Double.NaN);
  scalarScene("09 Outlet - pressure Pa",mid,ff("Pressure"),domainXmax-.6,2,.8,true,Double.NaN,Double.NaN);
  scalarScene("10 Outlet - speed m per s",mid,ff("Velocity").getMagnitudeFunction(),domainXmax-.6,2,.8,true,0,50);
  scalarScene("11 Outlet - instantaneous streamlines",streams("Inspect streamlines near outlet",domainXmax-.3,1,3,55),ff("Velocity").getMagnitudeFunction(),domainXmax-.6,2,.8,false,0,50);
  scalarScene("12 Free-surface close-up - water fraction",mid,ff("VolumeFractionwater"),-5,2,1.2,false,0,1);
  ArrayList<String> names=new ArrayList<>();for(Scene sc:inspectionScenes)names.add(sc.getPresentationName());
  Files.writeString(out.resolve("inspection_views.json"),json(Map.of("scenes",names,"plane_y_m",.02,"iso_alpha",.5,"outlet_x_bounds_m",List.of(domainXmax-.4,domainXmax),"note","Saved native scenes. Streamlines are instantaneous, not particle histories. Cell mass imbalance is kg/s and must not be volume weighted. Colors update from saved fields; automatic ranges are used for signed imbalance and pressure.")));
 }
 private void exportOutlet(double t)throws Exception{
  for(NamedObject part:List.of(outletCells,reg.getBoundaryManager().getBoundary("DOMAIN.outlet"))){
   boolean face=part instanceof Boundary;XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(part);tab.setRepresentation(fv);tab.setExtractVertexData(false);
   ArrayList<FieldFunction> fields=new ArrayList<>();for(String name:face?List.of("VolumeFractionwater","Pressure","MassFlowRatewater","MassFlowRateair"):List.of("VolumeFractionwater","Pressure","MassImbalancewater","MassImbalanceair","CourantNumber","Density"))fields.add(ff(name));
   FieldFunction vel=ff("Velocity");fields.add(vel.getComponentFunction(0));fields.add(vel.getComponentFunction(2));fields.add(vel.getMagnitudeFunction());tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(String.format(Locale.ROOT,(face?"outlet_faces":"outlet_cells")+"_t%.3f.csv",t)).toString());
   s.getTableManager().removeObjects(tab);
  }
 }
 private void guardedStartup(ImplicitUnsteadySolver us,MaxReport vmax,MaxReport cfl,MinReport amin,MaxReport amax,MassConservationErrorReport nw,MassConservationErrorReport na)throws Exception{
  us.getTimeStep().setValue(.0005);for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(50);
  try(var h=Files.newBufferedWriter(out.resolve("startup_history.csv"))){
   h.write("time_s,step,max_speed_m_s,max_CFL,alpha_min,alpha_max,Fx_N,Fz_N,native_water_kg_s,native_air_kg_s\n");
   for(int i=1;i<=40;i++){
    if(stopRequested())throw new IllegalStateException("User stop during guarded startup");
    s.getSimulationIterator().step(1);double t=s.getSolution().getPhysicalTime(),v=vmax.getReportMonitorValue(),c=cfl.getReportMonitorValue(),mi=amin.getReportMonitorValue(),ma=amax.getReportMonitorValue();double[] f=forces();
    if(!Double.isFinite(v)||!Double.isFinite(c)||!Double.isFinite(mi)||!Double.isFinite(ma)||v>50||mi< -1e-8||ma>1.00000001||Math.abs(t-i*.0005)>1e-8)throw new IllegalStateException("Guarded foil startup stability failure");
    h.write(t+","+i+","+v+","+c+","+mi+","+ma+","+f[0]+","+f[1]+","+nw.getReportMonitorValue()/.0005+","+na.getReportMonitorValue()/.0005+"\n");h.flush();
    if(i%5==0)Files.writeString(out.resolve("progress.json"),json(Map.of("stage","guarded foil startup","time_s",t,"steps",i,"max_speed_m_s",v,"dt_s",.0005,"inner",50)));
   }
  }
  s.saveState(out.resolve("checkpoint_startup_t0.020.sim").toString());
  us.getTimeStep().setValue(.001);for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);
  Files.writeString(out.resolve("startup_acceptance.json"),json(Map.of("status","guarded_startup_completed","time_s",s.getSolution().getPhysicalTime(),"steps",40,"dt_s",.0005,"inner",50,"next_dt_s",.001,"next_inner",10)));
 }

 public void execute(){s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_OUT")));
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable input copy required");
   if(Files.exists(out.resolve("history.csv")))throw new IllegalStateException("Attempt already used");
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");
   double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));
   domainXmin=Double.parseDouble(System.getenv("NTNU_CFG_XMIN"));domainXmax=Double.parseDouble(System.getenv("NTNU_CFG_XMAX"));requestedLambda=Double.parseDouble(System.getenv("NTNU_CFG_LAMBDA"));
   if(!List.of(10.,20.,30.,40.).contains(requestedLambda)||domainXmin>=-2||domainXmax<=3)throw new IllegalStateException("Unrecognized campaign domain");
   if(Math.abs(dt-.001)>1e-12||steps<30||steps>50000)throw new IllegalStateException("Manual run requires 1 ms and a bounded target");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()!=Long.parseLong(System.getenv("NTNU_WAVE_CELLS"))||Math.abs(s.getSolution().getPhysicalTime())>1e-8)throw new IllegalStateException("Input state mismatch");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
   for(Object x:s.getSolverStoppingCriterionManager().getChildren()){
    if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
    if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);((SolverStoppingCriterion)x).setIsUsed(true);}
   }
   ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-dt)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("Inspect must retain checkpoint SO 1 ms settings");
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   ManagedVofWave selectedWave=reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();
   double requestedHeight=Double.parseDouble(System.getenv("NTNU_WAVE_HEIGHT")),wavePeriod=0;boolean reinitialized=false;
   if(requestedHeight==0){if(!(selectedWave instanceof FlatVofWave))throw new IllegalStateException("Calm source mismatch");}
   else{
    if(!(selectedWave instanceof FifthOrderVofWave))throw new IllegalStateException("Fifth-order source required");
    FifthOrderVofWave wave=(FifthOrderVofWave)selectedWave;
    if(!List.of(.25,.5,.75).contains(requestedHeight)||wave.getFirstWaveFront()||Math.abs(wave.getWaterDepth().getValue()-24)>1e-8||Math.abs(wave.getVofWaveSpecification().getWaveLength().getValue()-requestedLambda)>1e-6)throw new IllegalStateException("Wave scope mismatch");
    if(Math.abs(wave.getWaveHeight().getValue()-requestedHeight)>1e-9){wave.getWaveHeight().setValue(requestedHeight);s.getSolution().clearSolution();s.getSolution().initializeSolution();reinitialized=true;}
    if(Math.abs(wave.getWaveHeight().getValue()-requestedHeight)>1e-9||Math.abs(wave.getVofWaveSpecification().getWaveLength().getValue()-requestedLambda)>1e-6)throw new IllegalStateException("Wave parameter getter mismatch");
    wavePeriod=wave.getWavePeriod().getValue();
    if(!Double.isFinite(wavePeriod)||wavePeriod<=0)throw new IllegalStateException("Invalid encounter period");
   }
   Files.writeString(out.resolve("requested_wave_audit.json"),json(Map.of("height_m",requestedHeight,"wavelength_m",requestedLambda,"depth_m",24,"period_s",wavePeriod,"class",selectedWave.getClass().getSimpleName(),"reinitialized",reinitialized,"physical_time_s",s.getSolution().getPhysicalTime())));

   double initialTime=s.getSolution().getPhysicalTime();
   Boundary outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet"),bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom");
   if(!String.valueOf(outlet.getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()).equals("ENVIRONMENTAL")||!String.valueOf(bed.getConditions().get(WallShearStressOption.class).getSelectedElement()).equals("SLIP"))throw new IllegalStateException("Checkpoint boundary settings mismatch");
   Files.writeString(out.resolve("continuation_identity.json"),json(Map.of("initial_time_s",initialTime,"target_time_s",.020+steps*dt,"reinitialized",reinitialized,"outlet_backflow","ENVIRONMENTAL","bottom","SLIP","scope","User-selected exploratory case: see request and requested_wave_audit. Guarded startup0.5ms50inner40steps then SO1ms10inner; pressuretol0.01. User accepts prior observed mass deviation for exploration; original0.01percent remains a diagnostic flag.")));
   FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
   FieldFunction theory=pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
   FieldFunction one=s.getFieldFunctionManager().getFunction("FoilPrepUnit");
   double[] xs=Arrays.stream(System.getenv("NTNU_CFG_GAUGES").split(",")).mapToDouble(Double::parseDouble).toArray();
   ArrayList<SurfaceIntegralReport> actual=new ArrayList<>(),analytic=new ArrayList<>();
   for(double x:xs){PlaneSection p=s.getPartManager().createPlaneSection();p.getInputParts().setObjects(reg);p.setOrigin(new DoubleVector(new double[]{x,.02,2}));p.setOrientation(new DoubleVector(new double[]{1,0,0}));actual.add(integral(p,alpha));analytic.add(integral(p,theory));
    SurfaceIntegralReport ar=s.getReportManager().createReport(SurfaceIntegralReport.class);ar.setFieldFunction(one);ar.setRepresentation(fv);ar.getParts().setObjects(p);if(Math.abs(ar.getReportMonitorValue()/.02-30)>.0001)throw new IllegalStateException("Gauge area mismatch at "+x);
   }
   MaxReport vmax=max("Wave_MaxSpeed",s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction(),reg),cfl=max("Wave_MaxCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),reg),amax=max("Wave_MaxAlpha",alpha,reg);
   MinReport amin=s.getReportManager().createReport(MinReport.class);amin.setRepresentation(fv);amin.setFieldFunction(alpha);amin.getParts().setObjects(reg);
   ThresholdPart inter=s.getPartManager().createThresholdPart();inter.getInputParts().setObjects(reg);inter.setFieldFunction(alpha);inter.setRange(new DoubleVector(new double[]{.01,.99}));inter.setMode(ThresholdMode.BETWEEN_TAG);
   MaxReport icfl=max("Wave_InterfaceCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),inter);
   VolumeIntegralReport mass=s.getReportManager().createReport(VolumeIntegralReport.class);mass.setRepresentation(fv);mass.setFieldFunction(s.getFieldFunctionManager().getFunction("Density"));mass.getParts().setObjects(reg);
   VolumeIntegralReport water=s.getReportManager().createReport(VolumeIntegralReport.class);water.setRepresentation(fv);water.setFieldFunction(alpha);water.getParts().setObjects(reg);
   ArrayList<String> fluxNames=new ArrayList<>();ArrayList<MassFlowReport> flux=new ArrayList<>();for(Boundary b:reg.getBoundaryManager().getBoundaries()){MassFlowReport r=s.getReportManager().createReport(MassFlowReport.class);r.getParts().setObjects(b);r.setRepresentation(fv);flux.add(r);fluxNames.add(b.getPresentationName());}
   Files.writeString(out.resolve("setup.json"),json(Map.of("cells",fv.getCellCount(),"dt_s",dt,"inner",10,"order","SECOND_ORDER","wave_period_s",wavePeriod,"steps",steps,"gpu_count",s.getNumberOfGpgpus(),"scope","First exploratory foil-wave trial with user-authorized mass-review exception; 0.01% remains reported, not a claim of verified force accuracy")));
   VolumeIntegralReport analyticWater=s.getReportManager().createReport(VolumeIntegralReport.class);analyticWater.setRepresentation(fv);analyticWater.setFieldFunction(theory);analyticWater.getParts().setObjects(reg);

   Continuum waterPhase=phase(pc,"water"),airPhase=phase(pc,"air");
   MassConservationErrorReport nativeWater=nativeError("Inspect_NativeWater_MassConservationError",waterPhase),nativeAir=nativeError("Inspect_NativeAir_MassConservationError",airPhase);
   Map<String,Object> sourceState=new LinkedHashMap<>();boolean sourceOptionFound=false;
   for(Object source:reg.getConditions().getChildren())if(source.getClass().getSimpleName().equals("MmpUserSourceOption")){
    Object enabled=source.getClass().getMethod("getUserSourceOption").invoke(source);sourceState.put("phase_source_term_enabled",enabled);sourceState.put("source_option_class",source.getClass().getName());sourceOptionFound=true;
    if(!Boolean.FALSE.equals(enabled))throw new IllegalStateException("Unexpected active phase mass source; diagnostic scope requires no source changes");
   }
   if(!sourceOptionFound)throw new IllegalStateException("Phase source option state could not be audited");
   ArrayList<Object> phaseModels=new ArrayList<>();
   for(Continuum phaseObject:List.of(waterPhase,airPhase)){
    ArrayList<String> phaseModelNames=new ArrayList<>();for(Object mod:phaseObject.getModelManager().getChildren())phaseModelNames.add(mod.getClass().getName());
    phaseModels.add(Map.of("phase",phaseObject.getPresentationName(),"models",phaseModelNames));
   }
   sourceState.put("phase_models",phaseModels);sourceState.put("reports",List.of(nativeDefinition(nativeWater),nativeDefinition(nativeAir)));
   sourceState.put("time_discretization",String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()));sourceState.put("dt_s",dt);
   sourceState.put("native_error_units","kg per physical step; divide by dt_s to obtain kg/s");
   sourceState.put("existing_gate_pct_of_inlet",.01);
   sourceState.put("native_comparison_caveat","Native phase report represents transport-equation iteration error. Check agreement with BDF2 density inventory and boundary FaceFlux before interpreting their difference; do not replace one with the other silently.");
   ArrayList<SumReport> phaseWaterFlux=new ArrayList<>(),phaseAirFlux=new ArrayList<>();
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    SumReport wr=s.getReportManager().createReport(SumReport.class),ar=s.getReportManager().createReport(SumReport.class);
    wr.setPresentationName("Inspect_Water_MassFlowRate_"+b.getPresentationName());ar.setPresentationName("Inspect_Air_MassFlowRate_"+b.getPresentationName());
    wr.setFieldFunction(s.getFieldFunctionManager().getFunction("MassFlowRatewater"));ar.setFieldFunction(s.getFieldFunctionManager().getFunction("MassFlowRateair"));
    for(SumReport pr:List.of(wr,ar)){pr.setRepresentation(fv);pr.setSmooth(false);pr.getParts().setObjects(b);}
    phaseWaterFlux.add(wr);phaseAirFlux.add(ar);
   }
   sourceState.put("phase_flux_fields",List.of("MassFlowRatewater","MassFlowRateair"));sourceState.put("phase_flux_reduction","Unsmoothed boundary-face SumReport; native kg/s values, positive outflow. No multiplication by face area. Native MassFlux[phase] has the opposite sign convention and is not used.");
   Files.writeString(out.resolve("native_phase_report_setup.json"),json(sourceState));
   setupForces();setupViews();s.saveState(out.resolve("inspection_setup.sim").toString());
   ReportMonitor waterInner,airInner;
   AMGLinearSolver vofAmg=s.getSolverManager().getSolver(SegregatedVofSolver.class).getAMGLinearSolver();
   AMGLinearSolver pressureAmg=s.getSolverManager().getSolver(star.segregatedflow.SegregatedFlowSolver.class).getPressureSolver().getAMGLinearSolver();
   for(AMGLinearSolver amg:List.of(vofAmg,pressureAmg))if(Math.abs(amg.getConvergeTol()-.1)>1e-12||amg.getMaxCycles()!=30||amg.getEpsilon()!=0)throw new IllegalStateException("BaselineAMGsettingsdiffer");
   pressureAmg.setConvergeTol(.01);
   if(Math.abs(vofAmg.getConvergeTol()-.1)>1e-12||Math.abs(pressureAmg.getConvergeTol()-.01)>1e-12)throw new IllegalStateException("Single-control pressure tolerance change failed");
   guardedStartup(us,vmax,cfl,amin,amax,nativeWater,nativeAir);initialTime=s.getSolution().getPhysicalTime();
   waterInner=everyInner(nativeWater);airInner=everyInner(nativeAir);
   Files.writeString(out.resolve("linear_trace_setup.json"),json(Map.of("VOF_tolerance",vofAmg.getConvergeTol(),"pressure_tolerance",pressureAmg.getConvergeTol(),"max_cycles",30,"epsilon",0,"trace_start_s",.605,"trace_end_s",.635,"native_monitor_update_mode",String.valueOf(waterInner.getStarUpdate().getUpdateModeOption().getSelectedElement()),"native_monitor_frequency",getter(waterInner.getStarUpdate().getIterationUpdateFrequency(),"getIterationFrequencyDefinition"),"scope","Only numericalchange pressure relativeAMGtolerance0.1to0.01; VOFtol0.1, allothercontrols unchanged; everyinnernative and LOWtrace retained")));
   SumReport zw=cellSum("MassImbalancewater"),za=cellSum("MassImbalanceair");zw.getParts().setObjects(outletCells);za.getParts().setObjects(outletCells);zw.setPresentationName("Inspect last outlet columns water imbalance kg/s");za.setPresentationName("Inspect last outlet columns air imbalance kg/s");zoneWaterMonitor=innerMonitor(zw);zoneAirMonitor=innerMonitor(za);
   s.getPlotManager().createMonitorPlot(List.of(waterInner,airInner),"Inspect - Native phase error kg per step");s.getPlotManager().createMonitorPlot(List.of(zoneWaterMonitor,zoneAirMonitor),"Inspect - Outlet column imbalance kg per second");
   long previousVofCycles=vofAmg.getTotalNumberCycles(),previousPressureCycles=pressureAmg.getTotalNumberCycles();
   Files.writeString(out.resolve("amg_cycle_counts.csv"),"time_s,step,vof_total_cycles,pressure_total_cycles,vof_cycles_this_step,pressure_cycles_this_step\n");
   SumReport localWater=cellSum("MassImbalancewater"),localAir=cellSum("MassImbalanceair"),localMixture=cellSum("MassImbalance");
   double previousMass=Double.NaN,secondPreviousMass=Double.NaN;int eventExports=0;

   long start=System.nanoTime();String status="target_reached";int done=0;
   try(var h=Files.newBufferedWriter(out.resolve("history.csv"));var g=Files.newBufferedWriter(out.resolve("gauges.csv"));var bfout=Files.newBufferedWriter(out.resolve("boundary_flux.csv"));var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"));var nb=Files.newBufferedWriter(out.resolve("native_phase_budget.csv"));var pf=Files.newBufferedWriter(out.resolve("boundary_phase_flux.csv"))){
    h.write("time_s,step,wall_s,max_speed_m_s,max_CFL,interface_CFL,alpha_min,alpha_max,mass_kg,water_volume_m3,net_outward_mass_kg_s,inward_mass_kg_s,vof_substeps,CD,CL_total,Fx_slice_N,Fz_slice_N,pressure_drag_N,viscous_drag_N\n");
    g.write("time_s,x_m,eta_actual_m,eta_analytic_m\n");bfout.write("time_s,boundary,outward_mass_kg_s\n");av.write("time_s,actual_water_m3,analytic_water_m3\n");
    pf.write("time_s,step,boundary,water_outward_mass_kg_s,air_outward_mass_kg_s,phase_sum_outward_mass_kg_s,faceflux_outward_mass_kg_s\n");
    nb.write("time_s,step,dt_s,native_water_error_kg_step,native_air_error_kg_step,native_sum_error_kg_step,native_water_error_kg_s,native_air_error_kg_s,native_sum_error_kg_s,native_sum_pct_inward_mass,native_abs_sum_pct_inward_mass,bdf2_accumulation_kg_s,faceflux_net_outward_kg_s,bdf2_plus_faceflux_kg_s,bdf2_plus_faceflux_pct_inward_mass,inward_mass_kg_s,phase_net_outward_kg_s,bdf2_plus_phaseflux_kg_s,bdf2_plus_phaseflux_pct_inward_mass,faceflux_minus_phaseflux_kg_s,native_water_error_log,native_air_error_log\n");
    Files.writeString(out.resolve("step_performance.csv"),"time_s,step,solver_call_s,diagnostics_and_output_s,total_loop_s\n");
    for(int step=0;step<=steps;step++){
     long loopStart=System.nanoTime(),solveStart=loopStart,solveEnd=loopStart;
     if(step>0){if(stopRequested()){status="stopped_by_marker";break;}double upcoming=initialTime+step*dt;boolean trace=upcoming>=.605-1e-9&&upcoming<=.635+1e-9;vofAmg.setVerbosity(trace?AMGVerbosity.LOW:AMGVerbosity.NONE);pressureAmg.setVerbosity(trace?AMGVerbosity.LOW:AMGVerbosity.NONE);solveStart=System.nanoTime();s.getSimulationIterator().step(1);solveEnd=System.nanoTime();done=step;}
     double t=s.getSolution().getPhysicalTime(),v=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),ci=icfl.getReportMonitorValue(),mn=amin.getReportMonitorValue(),mx=amax.getReportMonitorValue(),m=mass.getReportMonitorValue(),w=water.getReportMonitorValue(),net=0,in=0,wall=(System.nanoTime()-start)*1e-9;
     for(int k=0;k<flux.size();k++){double q=flux.get(k).getReportMonitorValue();net+=q;if(q<0)in-=q;bfout.write(t+","+fluxNames.get(k)+","+q+"\n");}bfout.flush();double analyticInventory=analyticWater.getReportMonitorValue();if(Double.isFinite(analyticInventory)){av.write(t+","+w+","+analyticInventory+"\n");av.flush();}else if(step==0){Files.writeString(out.resolve("reference_cache_at_load.json"),json(Map.of("time_s",t,"state","Analytic wave inventory unavailable immediately after checkpoint load; independent physical fields checked before first step","reinitialized",false)));}else throw new IllegalStateException("Analytic wave cache still unavailable after first step");
     if(!Double.isFinite(mn)||!Double.isFinite(mx)||!Double.isFinite(w)||!Double.isFinite(v)||!Double.isFinite(co)||!Double.isFinite(ci)||!Double.isFinite(m)||!Double.isFinite(net)||v>50||mn< -1e-8||mx>1.00000001||Math.abs(t-(initialTime+step*dt))>dt*.1){status="stability_guard";break;}

     long vc=vofAmg.getTotalNumberCycles(),pcCycles=pressureAmg.getTotalNumberCycles();if(step>0)Files.writeString(out.resolve("amg_cycle_counts.csv"),t+","+step+","+vc+","+pcCycles+","+(vc-previousVofCycles)+","+(pcCycles-previousPressureCycles)+"\n",StandardOpenOption.APPEND);previousVofCycles=vc;previousPressureCycles=pcCycles;
     double phaseNet=0;
     for(int k=0;k<flux.size();k++){
      double pw=phaseWaterFlux.get(k).getReportMonitorValue(),pa=phaseAirFlux.get(k).getReportMonitorValue();
      if(step>0&&(!Double.isFinite(pw)||!Double.isFinite(pa)))throw new IllegalStateException("Nonfinite native phase boundary mass flow after a guarded step");
      phaseNet+=pw+pa;
      if(step>0)pf.write(t+","+step+","+fluxNames.get(k)+","+pw+","+pa+","+(pw+pa)+","+flux.get(k).getReportMonitorValue()+"\n");
     }pf.flush();
     double nw=nativeWater.getReportMonitorValue(),na=nativeAir.getReportMonitorValue();
     String nwLog=nativeWater.getErrorLog(),naLog=nativeAir.getErrorLog();
     if(step==0){
      Map<String,Object> cache=new LinkedHashMap<>();cache.put("time_s",t);cache.put("water_kg_step",nw);cache.put("air_kg_step",na);cache.put("native_phase_flux_net_kg_s",phaseNet);cache.put("water_error_log",nwLog);cache.put("air_error_log",naLog);cache.put("state","Checkpoint-load report cache only; not accepted as a post-step native transport diagnostic. Both phase reports must be finite after the first guarded step.");
      Files.writeString(out.resolve("native_phase_cache_at_load.json"),json(cache));
     }else{
      if(!Double.isFinite(nw)||!Double.isFinite(na)){Files.writeString(out.resolve("native_phase_error.json"),json(Map.of("time_s",t,"water_error_log",String.valueOf(nwLog),"air_error_log",String.valueOf(naLog))));throw new IllegalStateException("Nonfinite native phase conservation error after a guarded step");}
      double nativeSum=(nw+na)/dt;
      double accumulation=step>=2?(1.5*m-2*previousMass+.5*secondPreviousMass)/dt:Double.NaN;
      double budget=accumulation+net;
      nb.write(t+","+step+","+dt+","+nw+","+na+","+(nw+na)+","+(nw/dt)+","+(na/dt)+","+nativeSum+","+(100*nativeSum/in)+","+(100*(Math.abs(nw)+Math.abs(na))/dt/in)+","+accumulation+","+net+","+budget+","+(100*budget/in)+","+in+","+phaseNet+","+(accumulation+phaseNet)+","+(100*(accumulation+phaseNet)/in)+","+(net-phaseNet)+","+String.valueOf(nwLog).replace(",",";").replace("\n"," ")+","+String.valueOf(naLog).replace(",",";").replace("\n"," ")+"\n");nb.flush();
     }
     if(step>0 && (step%1000==0 || ((100*(Math.abs(nw)+Math.abs(na))/dt/in)>.01 && eventExports<6))){localSnapshot(t,nw/dt,na/dt,localWater,localAir,localMixture);eventExports++;}
     if(step>0 && (step%25==0 || step<=3))exportOutlet(t);
     secondPreviousMass=previousMass;previousMass=m;
     double[] load=forces();h.write(t+","+step+","+wall+","+v+","+co+","+ci+","+mn+","+mx+","+m+","+w+","+net+","+in+","+s.getSolverManager().getSolver(SegregatedVofSolver.class).getSubStepCount()+","+load[0]/3855.6+","+load[1]/3855.6+","+load[0]+","+load[1]+","+load[2]+","+load[3]+"\n");h.flush();
     if(step==1||step%10==0){for(int k=0;k<xs.length;k++){double a=actual.get(k).getReportMonitorValue()/.02-24,b=analytic.get(k).getReportMonitorValue()/.02-24;if(step==0&&!Double.isFinite(b)&&Double.isFinite(a)&&Math.abs(a)<=1.5){Files.writeString(out.resolve("reference_gauges_at_load.json"),json(Map.of("time_s",t,"state","Analytic plane cache unavailable at load; require finite reference after first guarded step","reinitialized",false)));continue;}if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>1.5){Files.writeString(out.resolve("gauge_error.json"),json(Map.of("time_s",t,"x_m",xs[k],"actual_eta_m",a,"analytic_eta_m",b,"actual_error",actual.get(k).getErrorLog(),"analytic_error",analytic.get(k).getErrorLog())));throw new IllegalStateException("Invalid wave gauge at x="+xs[k]+" actual="+a+" analytic="+b);}g.write(t+","+xs[k]+","+a+","+b+"\n");}g.flush();Files.writeString(out.resolve("progress.json"),json(Map.of("time_s",t,"steps",step,"wall_s",wall,"max_speed_m_s",v,"interface_CFL",ci,"CD",load[0]/3855.6,"CL_total",load[1]/3855.6)));}
     if(step>0&&step%1000==0){String cp=String.format(Locale.ROOT,"checkpoint_t%.3f.sim",t);s.saveState(out.resolve(cp).toString());Files.writeString(out.resolve("latest_checkpoint.json"),json(Map.of("file",out.resolve(cp).toString(),"time_s",t,"completed_save",true)));zoneWaterMonitor.export(out.resolve("outlet_water_per_inner.csv").toString());zoneAirMonitor.export(out.resolve("outlet_air_per_inner.csv").toString());}
     Files.writeString(out.resolve("step_performance.csv"),t+","+step+","+((solveEnd-solveStart)*1e-9)+","+((System.nanoTime()-solveEnd)*1e-9)+","+((System.nanoTime()-loopStart)*1e-9)+"\n",StandardOpenOption.APPEND);
     if(wall>Double.parseDouble(System.getenv("NTNU_WAVE_WALL_S"))){status="wall_budget";break;}
    }
   }
   zoneWaterMonitor.export(out.resolve("outlet_water_per_inner.csv").toString());zoneAirMonitor.export(out.resolve("outlet_air_per_inner.csv").toString());
   waterInner.export(out.resolve("native_water_per_inner.csv").toString());airInner.export(out.resolve("native_air_per_inner.csv").toString());
   long waterSamples,airSamples;
   try(var lines=Files.lines(out.resolve("native_water_per_inner.csv"))){waterSamples=lines.filter(x->x.trim().matches("\"?[-+]?[0-9].*")).count();}
   try(var lines=Files.lines(out.resolve("native_air_per_inner.csv"))){airSamples=lines.filter(x->x.trim().matches("\"?[-+]?[0-9].*")).count();}
   Files.writeString(out.resolve("native_inner_sampling_audit.json"),json(Map.of("expected_inner_samples",done*10,"water_samples",waterSamples,"air_samples",airSamples,"completed_physical_steps",done,"expected_per_step",10)));
   if(waterSamples<done*10||airSamples<done*10||waterSamples>done*10+10||airSamples>done*10+10)throw new IllegalStateException("Nativeperinner samplecount mismatch");
   XyzInternalTable fieldTable=s.getTableManager().createTable(XyzInternalTable.class);fieldTable.getParts().setObjects(reg);fieldTable.setRepresentation(fv);fieldTable.setExtractVertexData(false);
   FieldFunction velocity=s.getFieldFunctionManager().getFunction("Velocity");
   fieldTable.setFieldFunctions(List.of(velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),velocity.getMagnitudeFunction(),alpha,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Density")));fieldTable.extract();fieldTable.export(out.resolve("checkpoint_fields.csv").toString());
   localSnapshot(s.getSolution().getPhysicalTime(),nativeWater.getReportMonitorValue()/dt,nativeAir.getReportMonitorValue()/dt,localWater,localAir,localMixture);exportOutlet(s.getSolution().getPhysicalTime());
   s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status",status,"steps",done,"time_s",s.getSolution().getPhysicalTime())));
   }catch(Exception e){try{if("User stop during guarded startup".equals(e.getMessage())){s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status","stopped_by_marker","stage","guarded startup","time_s",s.getSolution().getPhysicalTime(),"steps",0)));return;}Files.writeString(out.resolve("macro_error.txt"),e.toString());s.saveState(out.resolve("guard_or_error_preserved.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
