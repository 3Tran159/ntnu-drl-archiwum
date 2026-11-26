package macro;
import star.motion.*;import star.meshing.*;import star.common.*;import star.vis.*;import star.post.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.material.*;import star.segregatedflow.*;import star.turbulence.*;import star.kwturb.*;import star.vof.*;import star.mixturemultiphase.*;import star.vis.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class MiniVofStokes extends StarMacro {
 Simulation s;Path out,stop;Properties cfg=new Properties();Region reg;PhysicsContinuum pc;FifthOrderVofWave wave;FlatVofWave calm;double dt,sy=2.02128173276777,T=.45555302324319264,span=.02,start,amp,oldAmp,ramp;int inner;boolean foil;long deadline;
 ArrayList<Boundary>walls=new ArrayList<>(),flaps=new ArrayList<>(),outer=new ArrayList<>();Boundary inlet;
 Map<String,Report> rep=new LinkedHashMap<>();ArrayList<SurfaceIntegralReport>gauges=new ArrayList<>(),theory=new ArrayList<>();ArrayList<Double>gaugeAreas=new ArrayList<>();ArrayList<SurfaceIntegralReport> areaReports=new ArrayList<>();double[] xs={-6,-3,.952,4,8,12,16,20.5,24,27};XyzInternalTable fields,wallTable;double solveSeconds=0;int done=0;String reason="",result="HOLD_NOT_RUN";
 void writeResidualFactors(String file)throws Exception{Map<String,Object> factor=new LinkedHashMap<>();for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r){double[] values=r.getAllYValues();factor.put(r.getPresentationName(),Map.of("factor",r.getNormalizationType().getNormalizationFactor(),"mode",r.getNormalizationType().getClass().getSimpleName(),"normalized",r.isNormalized(),"stored_last",values.length>0?values[values.length-1]:Double.NaN));}write(file,factor);}
 double d(String k,double v){return Double.parseDouble(cfg.getProperty(k,""+v));} int i(String k,int v){return Integer.parseInt(cfg.getProperty(k,""+v));} boolean b(String k){return Boolean.parseBoolean(cfg.getProperty(k,"false"));}
 String json(Object a){if(a==null)return"null";if(a instanceof Number){double x=((Number)a).doubleValue();return Double.isFinite(x)?a.toString():"null";}if(a instanceof Boolean)return a.toString();if(a instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Object k:((Map<?,?>)a).keySet())j.add(json(k.toString())+":"+json(((Map<?,?>)a).get(k)));return j.toString();}if(a instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)a)j.add(json(x));return j.toString();}return"\""+a.toString().replace("\\","/").replace("\"","\\\"").replace("\n","\\n").replace("\r","")+"\"";}
 void write(String name,Object v)throws Exception{Path p=out.resolve(name),q=out.resolve(name+".tmp");Files.writeString(q,json(v));Files.move(q,p,StandardCopyOption.REPLACE_EXISTING);}
 void scalar(ScalarProfile p,double v){p.setMethod(ConstantScalarProfileMethod.class);p.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValue(v);}void sf(ScalarProfile p,FieldFunction f){p.setMethod(FunctionScalarProfileMethod.class);p.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}void vf(VectorProfile p,FieldFunction f){p.setMethod(FunctionVectorProfileMethod.class);p.getMethod(FunctionVectorProfileMethod.class).setFieldFunction(f);}void frac(VolumeFractionProfile p,FieldFunction f){p.setMethod(CompositeNMinus1ArrayProfileMethod.class);sf(p.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0),f);}
 FieldFunction ff(String n){FieldFunction f=s.getFieldFunctionManager().getFunction(n);if(f==null)throw new IllegalStateException("Missing field "+n);return f;}
 FieldFunction wf(VofWave w,String prefix){for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(prefix+w.getPresentationName()))return f;throw new IllegalStateException("Missing native wave field "+prefix+w.getPresentationName());}
 MinReport min(String name,FieldFunction f,Collection<? extends NamedObject> parts){MinReport r=s.getReportManager().createReport(MinReport.class);r.setPresentationName("NN_"+name);r.setFieldFunction(f);r.getParts().setObjects(parts);r.setSmooth(false);rep.put(name,r);return r;}
 MaxReport max(String name,FieldFunction f,Collection<? extends NamedObject> parts){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setPresentationName("NN_"+name);r.setFieldFunction(f);r.getParts().setObjects(parts);r.setSmooth(false);rep.put(name,r);return r;}
 boolean flatCflFallback=false;double v(String k){double value=rep.get(k).getReportMonitorValue();if(k.equals("interfaceCFL")&&!Double.isFinite(value)&&v("interfaceVolume")==0){if(b("calm_only"))return v("calmCorridorCFL");flatCflFallback=true;return v("CFL");}return value;}double loc(String k,int axis){Double x=((MinReport)rep.get(k)).getCollocatedValue(ff("Position").getComponentFunction(axis));return x==null?Double.NaN:x;}
 void status(String solver,String op)throws Exception{write("native_status.json",Map.of("solver_state",solver,"operation",op,"time_s",s.getSolution().getPhysicalTime(),"steps",done,"stage",cfg.getProperty("stage"),"night_approved",b("night")));}
 void save(String tag)throws Exception{status("STOPPED","SAVING");Path p=out.resolve(tag+".sim");if(Files.exists(p))throw new IllegalStateException("Refuse overwrite checkpoint "+p);s.saveState(p.toString());write("LATEST_CHECKPOINT.json",Map.of("path",p.toString(),"bytes",Files.size(p),"time_s",s.getSolution().getPhysicalTime(),"step_in_job",done,"solver_seconds",solveSeconds,"complete_write",true));status("STOPPED","CHECKPOINT_SAVED");}
 void createStokes(VofWaveModel vm,double oldAmp){wave=vm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,"CB_StokesV");wave.setHeavyFluidDensity(1000);wave.setLightFluidDensity(1.2);wave.setWaterDepth(sy+10);wave.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);wave.getVofWaveSpecification().getWaveLength().setValue(10);wave.getWaveHeight().setValue(Math.max(1e-6,2*oldAmp));wave.getPointOnLevel().setComponents(0,sy,0);wave.getVerticalDirection().setComponents(0,1,0);wave.getAdvancingDirection().setComponents(1,0,0);wave.getCurrent().setComponents(18,0,0);wave.getWind().setComponents(18,0,0);wave.setFirstWaveFront(false);}
 void prescribeRampTurbulence(InitialConditionManager init,VofWave flat) {
  init.get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
  scalar(init.get(TurbulentKineticEnergyProfile.class),.000486);
  sf(init.get(SpecificDissipationRateProfile.class),rampOmega(flat));
 }
 FieldFunction rampOmega(VofWave flat) {
  if(s.getFieldFunctionManager().hasFunction("CB_RampAmbientOmega"))return ff("CB_RampAmbientOmega");
  UserFieldFunction om=s.getFieldFunctionManager().createFieldFunction();
  om.setFunctionName("CB_RampAmbientOmega");
  om.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);
  Dimensions unit=new Dimensions();unit.setTime(-1);om.setDimensions(unit);
  om.setDefinition("<3.24 /s>+<45.36 /s>*${"+wf(flat,"Volume Fraction of Heavy Fluid of ").getFunctionName()+"}");
  return om;
 }

 void setCalmCurrent(FlatVofWave flat) {
  double duration=d("calm_speed_ramp_s",0);
  if(duration<=0){flat.getCurrent().setComponents(18,0,0);flat.getWind().setComponents(18,0,0);return;}
  if(!b("calm_only"))throw new IllegalStateException("Speed ramp allowed only in CALM");
  String target="[<0.05 m/s>+<17.95 m/s>*"+smooth("$Time/<"+duration+" s>")+",<0 m/s>,<0 m/s>]";
  flat.getCurrent().setDefinition(target);
  flat.getWind().setDefinition(target);
 }
 VofWave referenceWave(){return wave==null?calm:wave;}
 double nativePeriod(){return wave==null?0:wave.getWavePeriod().getSIValue();}
 double waveHeight(){return wave==null?0:wave.getWaveHeight().getSIValue();}
 void auditHydrostatics() throws Exception {
  List<Map<String,Object>> measurements=new ArrayList<>();
  boolean pass=true;
  for(double depth:new double[]{-1,1,2,5}){
   PointPart point=s.getPartManager().createPointPart();
   point.getInputParts().setObjects(reg);
   point.setPoint(new DoubleVector(new double[]{b("c01_seeded")?-11.5:-6,sy-depth,.01}));
   double p=max("HydroP"+depth,ff("AbsolutePressure"),List.of(point)).getReportMonitorValue();
   double alpha=max("HydroA"+depth,ff("VolumeFractionwater"),List.of(point)).getReportMonitorValue();
   double k=max("HydroK"+depth,ff("TurbulentKineticEnergy"),List.of(point)).getReportMonitorValue();
   double omega=max("HydroOmega"+depth,ff("SpecificDissipationRate"),List.of(point)).getReportMonitorValue();
   double target=101325+9.81*(depth<0?1.2:1000)*depth;
   pass &= Double.isFinite(p)&&Math.abs(p-target)<2000&&Math.abs(alpha-(depth>0?1:0))<.01&&k>1e-10&&omega>1e-10;
   measurements.add(Map.of("depth_m",depth,"pABS_Pa",p,"expected_pABS_Pa",target,"water_fraction",alpha,"k_m2_s2",k,"omega_s_inv",omega));
  }
  write("CALM_HYDROSTATIC_AUDIT.json",Map.of("pass",pass,"measurements",measurements));
  if(!pass)throw new IllegalStateException("CALM hydrostatic/VOF initial field audit failed");
 }
 void fresh()throws Exception{
  if(!s.getRegionManager().getRegions().isEmpty())throw new IllegalStateException("Fresh case required");s.getImportManager().importMeshFiles(cfg.getProperty("mesh"));reg=s.getRegionManager().getRegions().iterator().next();pc=s.getContinuumManager().createContinuum(PhysicsContinuum.class);pc.setPresentationName("MINI_URANS_VOF_2D");pc.enable(ThreeDimensionalModel.class);pc.enable(ImplicitUnsteadyModel.class);pc.enable(EulerianMultiPhaseModel.class);
  EulerianMultiPhaseModel mp=pc.getModelManager().getModel(EulerianMultiPhaseModel.class);EulerianPhase water=mp.createPhase();water.setPresentationName("water");water.enable(SinglePhaseLiquidModel.class);water.enable(ConstantDensityModel.class);Material wm=water.getModelManager().getModel(SinglePhaseLiquidModel.class).getMaterial();wm.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).setConstant(1000);EulerianPhase air=mp.createPhase();air.setPresentationName("air");air.enable(SinglePhaseGasModel.class);air.enable(ConstantDensityModel.class);Material am=air.getModelManager().getModel(SinglePhaseGasModel.class).getMaterial();am.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).setConstant(1.2);
  pc.enable(SegregatedVofModel.class);pc.enable(GravityModel.class);pc.enable(TurbulentModel.class);pc.enable(SegregatedVolumeFluxBasedFlowModel.class);pc.enable(RansTurbulenceModel.class);pc.enable(KOmegaTurbulence.class);pc.enable(SstKwTurbModel.class);pc.enable(KwAllYplusWallTreatment.class);pc.enable(VofWaveModel.class);wm.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).setConstant(.001);am.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).setConstant(1.8e-5);reg.setPhysicsContinuum(pc);pc.getReferenceValues().get(Gravity.class).setComponents(0,-9.81,0);pc.getReferenceValues().get(ReferencePressure.class).setValue(101325);pc.getReferenceValues().get(ReferenceDensity.class).setValue(1.2);pc.getReferenceValues().get(ReferenceAltitude.class).setComponents(0,sy,0);
  pc.getModelManager().getModel(SegregatedVolumeFluxBasedFlowModel.class).getUpwindOption().setSelected(FlowUpwindOption.Type.SECOND_ORDER);pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().setSelected(UpwindOption.Type.SECOND_ORDER);pc.getModelManager().getModel(SegregatedVofModel.class).setAngleFactor(.15);
  VofWaveModel vm=pc.getModelManager().getModel(VofWaveModel.class);vm.setEnableTheoryComparison(true);if(!b("calm_only"))createStokes(vm,oldAmp);
  VofWave initialWave=wave;if(oldAmp==0){FlatVofWave initFlat=vm.getVofWaveManager().createVofWave(FlatVofWave.class,"CB Initial Flat");initFlat.setHeavyFluidDensity(1000);initFlat.setLightFluidDensity(1.2);initFlat.getPointOnLevel().setComponents(0,sy,0);initFlat.getVerticalDirection().setComponents(0,1,0);setCalmCurrent(initFlat);initialWave=initFlat;}pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);scalar(pc.getInitialConditions().get(TurbulenceIntensityProfile.class),.001);scalar(pc.getInitialConditions().get(TurbulentViscosityRatioProfile.class),10);vf(pc.getInitialConditions().get(VelocityProfile.class),wf(initialWave,"Velocity of "));sf(pc.getInitialConditions().get(InitialPressureProfile.class),wf(initialWave,"Hydrostatic Pressure of Heavy Fluid of "));frac(pc.getInitialConditions().get(VolumeFractionProfile.class),wf(initialWave,"Volume Fraction of Heavy Fluid of "));if(b("calm_explicit_ambient"))prescribeRampTurbulence(pc.getInitialConditions(),initialWave);
 }
 void auditRecoveryStart() throws Exception {
  List<Map<String,Object>> readings=new ArrayList<>();
  boolean pass=true;
  for(double y:new double[]{sy-2,sy-1,sy+1}){
   PointPart q=s.getPartManager().createPointPart();
   q.getInputParts().setObjects(reg);
   q.setPoint(new DoubleVector(new double[]{-11.5,y,.01}));
   double u=max("RecoveryU"+y,ff("Velocity").getComponentFunction(0),List.of(q)).getReportMonitorValue();
   FieldFunction bound=inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction();
   if(!bound.equals(wf(calm,"Velocity of ")))throw new IllegalStateException("Unexpected CALM inlet binding");
   double imposed=(y>sy?calm.getWind():calm.getCurrent()).getSIVector().get(0);
   readings.add(Map.of("y_m",y,"field_Ux_m_s",u,"imposed_Ux_m_s",imposed));
   pass &= Math.abs(u-18)<.05&&Math.abs(imposed-18)<1e-9;
  }
  pass &= v("pmin")>12339.214766776897&&v("kmin")>1.0001e-10&&v("omin")>1.0001e-10
       &&v("volume")>0&&v("alphaMin")>=-1e-5&&v("alphaMax")<=1.00001;
  if(b("clean_calm")){
   Collection<Region> domain=List.of(reg);
   FieldFunction vel=ff("Velocity");
   double umin=min("CleanUMin",vel.getComponentFunction(0),domain).getReportMonitorValue();
   double umax=max("CleanUMax",vel.getComponentFunction(0),domain).getReportMonitorValue();
   double cross=0;
   for(int j=1;j<3;j++){
    double a=min("CleanCrossMin"+j,vel.getComponentFunction(j),domain).getReportMonitorValue();
    double c=max("CleanCrossMax"+j,vel.getComponentFunction(j),domain).getReportMonitorValue();
    cross=Math.max(cross,Math.max(Math.abs(a),Math.abs(c)));
   }
   boolean noZones=reg.getConditions().get(VofWaveZoneOption.class).getSelected()==VofWaveZoneOptionEnum.NONE;
   boolean noForcing=inlet.getConditions().getObjects().stream().noneMatch(c->c instanceof VofWaveForcingBoundaryOption o&&o.getSelectedElement()==VofWaveForcingBoundaryOption.Type.YES);
   pass &= Math.abs(umin-18)<1e-8&&Math.abs(umax-18)<1e-8&&cross<1e-8&&noZones&&noForcing;
   write("CLEAN_NATIVE_INITIALIZATION.json",Map.of("pass",pass,"Ux_min_m_s",umin,"Ux_max_m_s",umax,
    "crossflow_max_m_s",cross,"no_zone_forcing_or_damping",noZones,"no_inlet_forcing",noForcing,
    "pABSmin_Pa",v("pmin"),"k_min",v("kmin"),"omega_min",v("omin"),"far_field",readings));
  }
  write("RECOVERY_V3_INITIAL_AUDIT.json",Map.of("pass",pass,"far_field",readings,
    "domain_pABSmin_Pa",v("pmin"),"kmin",v("kmin"),"omega_min",v("omin"),
    "min_volume_m3",v("volume"),"min_alpha",v("alphaMin"),"max_alpha",v("alphaMax"),
    "vmax_m_s",v("vmax"),"vmax_xyz",List.of(maxLoc("vmax",0),maxLoc("vmax",1),maxLoc("vmax",2))));
  if(!pass)throw new IllegalStateException("V3 start field gate failed");
 }
 UserFieldFunction seededScalar(String name,Dimensions dims,String expression){
  UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();
  f.setFunctionName(name);f.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);
  f.setDimensions(dims);f.setDefinition(expression);return f;
 }
 double maxLoc(String k,int axis){
  Double x=((MaxReport)rep.get(k)).getCollocatedValue(ff("Position").getComponentFunction(axis));
  return x==null?Double.NaN:x;
 }

 void useSeededInitialFlow() throws Exception {
  String path=cfg.getProperty("flow_seed","");
  if(path.isBlank())return;
  if(!foil||!b("fresh")||moving)throw new IllegalStateException("V2 flow seed requires fresh fixed foil");
  Path seed=Paths.get(path).toRealPath();
  try(var in=Files.newInputStream(seed)){
   String digest=HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(in.readAllBytes()));
   if(!digest.equals(cfg.getProperty("flow_seed_sha256")))throw new IllegalStateException("Seed SHA mismatch");
  }
  Table data=s.getTableManager().createFromFile(seed.toString());
  data.setPresentationName("CB_V2_InitialFlow");
  String call="interpolatePositionTable(@Table(\"CB_V2_InitialFlow\"), ";
  UserFieldFunction uv=s.getFieldFunctionManager().createFieldFunction();
  uv.setFunctionName("CB_SeedInitialVelocity");
  uv.getTypeOption().setSelected(FieldFunctionTypeOption.Type.VECTOR);
  Dimensions vu=new Dimensions();vu.setLength(1);vu.setTime(-1);uv.setDimensions(vu);
  uv.setDefinition(call+"\"U\", \"V\", \"W\") * <1 m/s>");
  UserFieldFunction pressure=s.getFieldFunctionManager().createFieldFunction();
  pressure.setFunctionName("CB_SeedInitialPressure");
  pressure.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);
  Dimensions pu=new Dimensions();pu.setMass(1);pu.setLength(-1);pu.setTime(-2);pressure.setDimensions(pu);
  pressure.setDefinition(call+"\"P\") * <1 Pa>");
  vf(pc.getInitialConditions().get(VelocityProfile.class),uv);
  sf(pc.getInitialConditions().get(InitialPressureProfile.class),pressure);
  if(b("c01_seeded")){
   InitialConditionManager init=pc.getInitialConditions();
   init.get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
   Dimensions ku=new Dimensions();ku.setLength(2);ku.setTime(-2);
   Dimensions ou=new Dimensions();ou.setTime(-1);
   sf(init.get(TurbulentKineticEnergyProfile.class),seededScalar("C01_InitK",ku,call+"\"K\") * <1 m^2/s^2>"));
   sf(init.get(SpecificDissipationRateProfile.class),seededScalar("C01_InitOmega",ou,call+"\"O\") * <1 /s>"));
  }
 }

 void auditCorrectedNativeMesh() throws Exception {
  Region r=s.getRegionManager().getRegions().iterator().next();
  FvRepresentation mesh=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  long n=mesh.getCellCount();
  if(n==24515||n<10000||n>55000||!mesh.generateMeshReport(List.of(r)).getBoolean("success"))
   throw new IllegalStateException("Expected regenerated full-width refinement mesh; cells="+n);
  SimpleBlockPart band=null;
  for(GeometryPart part:s.get(SimulationPartManager.class).getLeafParts())
   if(part instanceof SimpleBlockPart block&&block.getPresentationName().startsWith("Free surface band"))band=block;
  if(band==null)throw new IllegalStateException("Free-surface control part missing");
  var a=band.getCorner1().getSIValue();var z=band.getCorner2().getSIValue();
  double xmin=Math.min(a.get(0),z.get(0)),xmax=Math.max(a.get(0),z.get(0));
  if(xmin>-12+1e-7||xmax<28-1e-7)
   throw new IllegalStateException("Free-surface band stops short: "+xmin+" to "+xmax);
  List<Boundary> ends=new ArrayList<>();
  for(Boundary b:r.getBoundaryManager().getBoundaries())
   if(Set.of("inlet","outlet").contains(b.getPresentationName()))ends.add(b);
  if(ends.size()!=2)throw new IllegalStateException("Inlet/outlet boundaries missing");
  XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);
  table.setPresentationName("Full-length free-surface band audit");
  table.getParts().setObjects(ends);table.setRepresentation(mesh);
  table.setFieldFunctions(List.of(ff("Area").getMagnitudeFunction()));table.extract();
  Path csv=out.resolve("FREE_SURFACE_END_FACES.csv");table.export(csv.toString(),",");
  List<Double> in=new ArrayList<>(),outletFaces=new ArrayList<>();
  for(String line:Files.readAllLines(csv).stream().skip(1).toList()){
   String[] v=line.split(",");
   double area=Double.parseDouble(v[0]),x=Double.parseDouble(v[1]),y=Double.parseDouble(v[2]);
   if(Math.abs(y-sy)<.18)(x<0?in:outletFaces).add(area/.02);
  }
  double inletMax=in.stream().mapToDouble(Double::doubleValue).max().orElse(Double.POSITIVE_INFINITY);
  double outletMax=outletFaces.stream().mapToDouble(Double::doubleValue).max().orElse(Double.POSITIVE_INFINITY);
  boolean pass=in.size()>=3&&outletFaces.size()>=3&&inletMax<=.15&&outletMax<=.15;
  write("FULL_LENGTH_MESH_AUDIT.json",Map.of("pass",pass,"cells",n,"xmin_m",xmin,"xmax_m",xmax,
    "inlet_band_faces",in.size(),"outlet_band_faces",outletFaces.size(),"inlet_max_edge_m",inletMax,"outlet_max_edge_m",outletMax));
  if(!pass)throw new IllegalStateException("Saved mesh does not resolve the free surface at both open boundaries");
 }

 void configure()throws Exception{
  if(b("clean_calm")&&(!b("calm_only")||(moving&&!b("calm_active_pilot"))||kinematics||amp!=0||oldAmp!=0
     ||d("calm_speed_ramp_s",0)!=0||b("calm_explicit_ambient")||b("c01_seeded")
     ||!cfg.getProperty("flow_seed","").isBlank()))throw new IllegalStateException("Clean CALM requires native fields and no imposed forcing");
  if(!b("fresh")){reg=s.getRegionManager().getRegions().iterator().next();pc=reg.getPhysicsContinuum();double expected=d("expected_time",-1);if(Math.abs(s.getSolution().getPhysicalTime()-expected)>1e-9)throw new IllegalStateException("Input physical time mismatch");VofWaveModel vm=pc.getModelManager().getModel(VofWaveModel.class);for(ManagedVofWave w:vm.getVofWaveManager().getObjects())if(w instanceof FifthOrderVofWave){if(wave!=null)throw new IllegalStateException("Ambiguous wave");wave=(FifthOrderVofWave)w;}if(wave==null&&!b("calm_only")){if(!b("from_calm")||oldAmp!=0||ramp<=0)throw new IllegalStateException("Missing native Stokes V");createStokes(vm,0);}if(wave!=null&&b("calm_only"))throw new IllegalStateException("CALM input contains a Stokes object");}
  else fresh();
  long nc=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();if((!b("native_remesh_initialize")&&nc!=i("expected_cells",foil?44442:41280))||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Mesh/GPU contract mismatch");
  start=s.getSolution().getPhysicalTime();VofWaveModel vm=pc.getModelManager().getModel(VofWaveModel.class);calm=vm.getVofWaveManager().createVofWave(FlatVofWave.class,"NN_OutletFlat");calm.setHeavyFluidDensity(1000);calm.setLightFluidDensity(1.2);calm.getPointOnLevel().setComponents(0,sy,0);calm.getVerticalDirection().setComponents(0,1,0);setCalmCurrent(calm);
  pc.getModelManager().getModel(SstKwTurbModel.class).getKwTurbRealizabilityOption().setSelected(KwTurbRealizabilityOption.Type.VORTICITY);
  reg.getConditions().get(VofWaveZoneOption.class).setSelected(b("clean_calm")?VofWaveZoneOptionEnum.NONE:VofWaveZoneOptionEnum.FORCING_DAMPING);
  if(!b("clean_calm")){
   reg.getConditions().get(ForcingLengthSpecificationOption.class).setSelected(LengthSpecificationOption.Type.BOUNDARY);
   reg.getConditions().get(DampingLengthSpecificationOption.class).setSelected(LengthSpecificationOption.Type.BOUNDARY);
   reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(amp==0&&oldAmp==0?calm:wave);
  }
  for(Boundary bb:reg.getBoundaryManager().getBoundaries()){
   String n=bb.getPresentationName();if(n.contains("inlet")){bb.setBoundaryType(InletBoundary.class);inlet=bb;outer.add(bb);VofWave inletWave=amp==0&&oldAmp==0?calm:wave;bb.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);vf(bb.getValues().get(VelocityProfile.class),wf(inletWave,"Velocity of "));frac(bb.getValues().get(VolumeFractionProfile.class),wf(inletWave,"Volume Fraction of Heavy Fluid of "));bb.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);scalar(bb.getValues().get(TurbulenceIntensityProfile.class),.001);scalar(bb.getValues().get(TurbulentViscosityRatioProfile.class),10);if(b("calm_explicit_ambient")){bb.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);scalar(bb.getValues().get(TurbulentKineticEnergyProfile.class),.000486);sf(bb.getValues().get(SpecificDissipationRateProfile.class),rampOmega(inletWave));}if(!b("clean_calm")){bb.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(VofWaveForcingBoundaryOption.Type.YES);scalar(bb.getValues().get(VofWaveForcingLength.class),d("forcing_length",4));}}
   else if(n.contains("outlet")||n.contains("top")){bb.setBoundaryType(PressureBoundary.class);outer.add(bb);sf(bb.getValues().get(StaticPressureProfile.class),wf(calm,"Hydrostatic Pressure of Heavy Fluid of "));frac(bb.getValues().get(VolumeFractionProfile.class),wf(calm,"Volume Fraction of Heavy Fluid of "));bb.getConditions().get(BackflowSpecification.class).getBackflowVelocityDirectionOption().setSelected(BackflowVelocityDirectionOption.Type.EXTRAPOLATED);bb.getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().setSelected(ReversedFlowPressureOption.Type.ENVIRONMENTAL);if(n.contains("outlet")&&!b("clean_calm")){bb.getConditions().get(VofWaveDampingBoundaryOption.class).setSelected(VofWaveDampingBoundaryOption.Type.YES);scalar(bb.getValues().get(VofWaveDampingLength.class),d("damping_length",8));}}
   else if(n.contains("span"))bb.setBoundaryType(SymmetryBoundary.class);else if(n.contains("bottom")){bb.setBoundaryType(WallBoundary.class);bb.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.SLIP);}else if(n.contains("main")||n.contains("flap")){bb.setBoundaryType(WallBoundary.class);walls.add(bb);if(n.contains("flap"))flaps.add(bb);}else throw new IllegalStateException("Unexpected boundary "+n);
  }
  if(foil&&(walls.size()!=2||flaps.size()!=1))throw new IllegalStateException("Foil groups incomplete");
  if(wave==null){if(amp!=0||oldAmp!=0||(moving&&!b("calm_active_pilot")))throw new IllegalStateException("Flat calm contract");}
  else if(Math.abs(amp-oldAmp)>1e-12){if(ramp<=0)throw new IllegalStateException("Continuous amplitude ramp required");String x="min(1.0,max(0.0,($Time-<"+d("ramp_origin_s",start)+" s>)/<"+ramp+" s>))";wave.getWaveHeight().setDefinition("<"+Math.max(1e-6,2*oldAmp)+" m>+<"+(2*amp-Math.max(1e-6,2*oldAmp))+" m>*(10*pow("+x+",3)-15*pow("+x+",4)+6*pow("+x+",5))");}else wave.getWaveHeight().setValue(Math.max(1e-6,2*amp));
  ImplicitUnsteadySolver un=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);un.getTimeStep().setValue(dt);un.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);PressureSolver ps=s.getSolverManager().getSolver(SegregatedFlowSolver.class).getPressureSolver();double oldUrf=ps.getUrf(),oldTol=ps.getAMGLinearSolver().getConvergeTol();ps.getAMGLinearSolver().setConvergeTol(d("pressure_tol",.01));ps.setUrf(d("pressure_urf",.5));
  for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){if(c instanceof PhysicalTimeStoppingCriterion||c instanceof StepStoppingCriterion)c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(inner);c.setIsUsed(true);}}
  s.getSimulationIterator().getAutoSave().setEnabled(false);if(b("fresh")){useSeededInitialFlow();s.getSolution().initializeSolution();}
  if(b("native_remesh_initialize")){
   if(b("fresh")||moving||start!=0||!b("clean_calm"))
    throw new IllegalStateException("Native remesh CALM initialization identity");
   auditCorrectedNativeMesh();
   InitialConditionManager initial=pc.getInitialConditions();
   initial.get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);
   scalar(initial.get(TurbulenceIntensityProfile.class),.001);
   scalar(initial.get(TurbulentViscosityRatioProfile.class),10);
   vf(initial.get(VelocityProfile.class),wf(calm,"Velocity of "));
   sf(initial.get(InitialPressureProfile.class),wf(calm,"Hydrostatic Pressure of Heavy Fluid of "));
   frac(initial.get(VolumeFractionProfile.class),wf(calm,"Volume Fraction of Heavy Fluid of "));
   s.getSolution().initializeSolution();
  }
double nativePeriod=nativePeriod();if(Double.isFinite(nativePeriod)&&nativePeriod>.40&&nativePeriod<.52){T=nativePeriod;W=2*Math.PI/T;}write("STOKES_READBACK.json",Map.of("wave_type",wave==null?"FlatVofWave":"FifthOrderVofWave","native_period_s",nativePeriod,"period_planning_s",wave==null?0:T,"height_m",waveHeight(),"depth_m",sy+10,"wavelength_m",wave==null?0:wave.getVofWaveSpecification().getWaveLength().getSIValue(),"advancing_direction","+X","current_m_s",18,"global_initialization",b("fresh")&&oldAmp>0));
  Map<String,Object>a=new LinkedHashMap<>();a.put("stage",cfg.getProperty("stage"));a.put("clean_unforced_calm",b("clean_calm"));a.put("cells",nc);a.put("start_time",start);a.put("dt",dt);a.put("inner",inner);a.put("initialization_called",b("fresh")||b("native_remesh_initialize"));a.put("calm_speed_ramp_s",d("calm_speed_ramp_s",0));a.put("explicit_ambient_k_omega",b("calm_explicit_ambient"));a.put("initial_calm_current_m_s",d("calm_speed_ramp_s",0)>0?.05:18);a.put("reset_on_loaded_fields",false);a.put("old_pressure_urf",oldUrf);a.put("pressure_urf",ps.getUrf());a.put("old_pressure_tol",oldTol);a.put("pressure_tol",ps.getAMGLinearSolver().getConvergeTol());a.put("amplitude_from",oldAmp);a.put("amplitude_target",amp);a.put("amplitude_ramp_s",ramp);a.put("initial_field",oldAmp==0?"flat water and air":"native Stokes V");a.put("inlet_ramp",ramp>0?"S5, zero endpoint first/second derivative":"Existing globally initialized wave; no velocity/amplitude jump");a.put("forcing_length_m",d("forcing_length",4));a.put("damping_length_m",d("damping_length",8));a.put("outlet_and_top","native flat-wave pressure and volume fraction");a.put("vorticity_limiter",pc.getModelManager().getModel(SstKwTurbModel.class).getKwTurbRealizabilityOption().getSelectedElement().toString());a.put("all_yplus",pc.getModelManager().hasModel(KwAllYplusWallTreatment.class)!=null);a.put("sst",pc.getModelManager().hasModel(SstKwTurbModel.class)!=null);a.put("reference_C01_CL",.3156595);a.put("reference_C01_CD",.00700232);a.put("C01_not_modified",true);write("SETUP_READBACK.json",a);
 }
 void reports()throws Exception{
  Collection<Region>rs=List.of(reg);FieldFunction alpha=ff("VolumeFractionwater"),co=ff("CourantNumber");ThresholdPart inter=s.getPartManager().createThresholdPart();inter.getInputParts().setObjects(reg);inter.setFieldFunction(alpha);inter.setRange(new DoubleVector(new double[]{.01,.99}));inter.setMode(ThresholdMode.BETWEEN_TAG);
  if(b("calm_only")){ThresholdPart strip=s.getPartManager().createThresholdPart();strip.getInputParts().setObjects(reg);strip.setFieldFunction(ff("Position").getComponentFunction(1));strip.setRange(new DoubleVector(new double[]{sy-.10,sy+.10}));strip.setMode(ThresholdMode.BETWEEN_TAG);max("calmCorridorCFL",co,List.of(strip));write("CALM_CFL_DEFINITION.json",Map.of("normal","max on mixed water cells","empty_mixed_set","max in +/-0.10 m strip about still-water level"));}max("interfaceCFL",co,List.of(inter));max("CFL",co,rs);max("alphaMax",alpha,rs);min("alphaMin",alpha,rs);MinReport p=min("pmin",ff("AbsolutePressure"),rs);p.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1),ff("Position").getComponentFunction(2)));
  min("quality",ff("CellQuality"),rs);min("volume",ff("Volume"),rs);min("face",ff("FaceValidity"),rs);min("kmin",ff("TurbulentKineticEnergy"),rs);min("omin",ff("SpecificDissipationRate"),rs);max("nut",ff("TurbulentViscosityRatio"),rs);MaxReport velocityPeak=max("vmax",ff("Velocity").getMagnitudeFunction(),rs);velocityPeak.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1),ff("Position").getComponentFunction(2)));max("vzmax",ff("Velocity").getComponentFunction(2),rs);min("vzmin",ff("Velocity").getComponentFunction(2),rs);
  VolumeIntegralReport mass=s.getReportManager().createReport(VolumeIntegralReport.class);mass.setFieldFunction(ff("Density"));mass.getParts().setObjects(reg);rep.put("mass",mass);MassFlowReport net=s.getReportManager().createReport(MassFlowReport.class),inf=s.getReportManager().createReport(MassFlowReport.class);net.getParts().setObjects(outer);inf.getParts().setObjects(inlet);rep.put("net",net);rep.put("influx",inf);
  // Eta from (water area - total fluid area)/span + top-SWL cancels the submerged foil column exactly.
  FieldFunction unity;if(s.getFieldFunctionManager().hasFunction("NN_ColumnUnity"))unity=ff("NN_ColumnUnity");else{UserFieldFunction u=s.getFieldFunctionManager().createFieldFunction();u.setFunctionName("NN_ColumnUnity");u.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);u.setDefinition("1");unity=u;}
  if(foil){VolumeIntegralReport volume=s.getReportManager().createReport(VolumeIntegralReport.class);volume.setFieldFunction(unity);volume.getParts().setObjects(reg);rep.put("fluidVolume",volume);}
  UserFieldFunction indicator=s.getFieldFunctionManager().createFieldFunction();indicator.setFunctionName("CB_MixedInterfaceCell");indicator.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);indicator.setDefinition("($VolumeFractionwater >= 0.01 && $VolumeFractionwater <= 0.99) ? 1 : 0");VolumeIntegralReport iVol=s.getReportManager().createReport(VolumeIntegralReport.class);iVol.setFieldFunction(indicator);iVol.getParts().setObjects(reg);rep.put("interfaceVolume",iVol);
  for(double x:xs){PlaneSection plane=s.getPartManager().createPlaneSection();plane.getInputParts().setObjects(reg);plane.setOrigin(new DoubleVector(new double[]{x,sy,.01}));plane.setOrientation(new DoubleVector(new double[]{1,0,0}));SurfaceIntegralReport area=s.getReportManager().createReport(SurfaceIntegralReport.class);area.setFieldFunction(unity);area.getParts().setObjects(plane);area.setSmooth(false);double ar=area.getReportMonitorValue();if(ar<=0||ar>.281)throw new IllegalStateException("Gauge area invalid "+ar);gaugeAreas.add(ar);areaReports.add(area);for(boolean target:new boolean[]{false,true}){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(target?wf(referenceWave(),"Volume Fraction of Heavy Fluid of "):alpha);r.getParts().setObjects(plane);r.setSmooth(false);(target?theory:gauges).add(r);}}
  PointPart point=s.getPartManager().createPointPart();point.getInputParts().setObjects(reg);point.setPoint(new DoubleVector(new double[]{foil?-1.19:.952,.02128173276777,.01}));max("ux",ff("Velocity").getComponentFunction(0),List.of(point));max("uy",ff("Velocity").getComponentFunction(1),List.of(point));max("ut",wf(referenceWave(),"Velocity of ").getComponentFunction(0),List.of(point));max("vt",wf(referenceWave(),"Velocity of ").getComponentFunction(1),List.of(point));
  if(foil){for(int axis=0;axis<2;axis++){ForceReport f=s.getReportManager().createReport(ForceReport.class);f.getDirection().setComponents(axis==0?1:0,axis==1?1:0,0);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getParts().setObjects(walls);rep.put(axis==0?"Fx":"Fz",f);}MomentReport mh=s.getReportManager().createReport(MomentReport.class);mh.getDirection().setComponents(0,0,-1);mh.getOrigin().setComponents(.952,.02128173276777,.01);mh.setPressureOption(FluidLoadsReportPressureOption.SP_UC);mh.getParts().setObjects(flaps);rep.put("Mh",mh);MinReport pb=min("pbody",ff("AbsolutePressure"),walls);pb.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1),ff("Position").getComponentFunction(2)));min("pflap",ff("AbsolutePressure"),flaps);min("ymin",ff("WallYplus"),walls);max("ymax",ff("WallYplus"),walls);AreaAverageReport yp=s.getReportManager().createReport(AreaAverageReport.class);yp.setFieldFunction(ff("WallYplus"));yp.getParts().setObjects(walls);rep.put("ymean",yp);}
  if(foil){for(ForceReportForceOption.Type type:List.of(ForceReportForceOption.Type.PRESSURE,ForceReportForceOption.Type.SHEAR)){ForceReport f=s.getReportManager().createReport(ForceReport.class);f.getForceOption().setSelected(type);f.getDirection().setComponents(1,0,0);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getParts().setObjects(walls);rep.put(type==ForceReportForceOption.Type.PRESSURE?"FxPressure":"FxShear",f);}wallTable=s.getTableManager().createTable(XyzInternalTable.class);wallTable.setPresentationName("CB_Wall_Cp_yplus");wallTable.getParts().setObjects(walls);wallTable.setFieldFunctions(List.of(ff("WallYplus"),ff("Pressure"),ff("AbsolutePressure")));}
  fields=s.getTableManager().createTable(XyzInternalTable.class);fields.setPresentationName("NIGHT_FIELDS");fields.getParts().setObjects(reg);fields.setFieldFunctions(List.of(alpha,ff("AbsolutePressure"),ff("Pressure"),ff("Velocity").getComponentFunction(0),ff("Velocity").getComponentFunction(1),ff("Velocity").getComponentFunction(2),ff("TurbulentKineticEnergy"),ff("SpecificDissipationRate"),ff("TurbulentViscosityRatio"),co,ff("CellQuality"),ff("Volume")));
 }
 String physical(int step,double bal){if(!Double.isFinite(bal)||(foil&&(!Double.isFinite(v("pbody"))||!Double.isFinite(v("pflap")))))return "NONFINITE_SAFETY_MEASUREMENT";if(!b("pressure_diagnostic_only")&&(v("pmin")<=12339.214766776897||(foil&&Math.min(v("pbody"),v("pflap"))<=12339.214766776897)))return"PRESSURE";if(v("quality")<=0||v("volume")<=0||v("face")<.5)return"MESH";if(v("interfaceCFL")>.5||v("CFL")>25)return"CFL";if(v("alphaMin")<-.00001||v("alphaMax")>1.00001)return"ALPHA";if(v("kmin")<=1.0001e-10||v("omin")<=1.0001e-10||v("nut")>=99999)return"TURBULENCE_LIMIT";if(v("vmax")>180)return"VELOCITY";if(step>5&&bal>1e-4)return"MASS";for(String k:List.of("pmin","quality","volume","face","interfaceCFL","CFL","kmin","omin","nut","vmax"))if(!Double.isFinite(v(k)))return"NONFINITE_"+k;return"";}
 
 static final double HX=.952, HY=.02128173276777; double W=2*Math.PI/.4536;
 boolean moving, kinematics;
 double referenceTipX, referenceTipY, previousAngle, previousTime;
 XyzInternalTable vertices;
 String smooth(String x){
  String q="min(1,max(0,"+x+"))";
  return "(10*pow("+q+",3)-15*pow("+q+",4)+6*pow("+q+",5))";
 }
 String motionTime(){return "($Time-<"+(start+d("motion_start_delay_s",0))+" s>)";}
 double localPhase(double time){return 2*Math.PI*HX/10-W*time+d("phase_offset_rad",0);}
 double smoothValue(double x){double q=Math.max(0,Math.min(1,x));return q*q*q*(10-15*q+6*q*q);}
 double targetAngle(double time){
  if(!moving)return 0;
  double elapsed=time-d("motion_origin_s",start)-d("motion_start_delay_s",0);
  if(kinematics||b("flow_cycle")){
   double a=d("flap_cycle_deg",2), q=d("flap_quarter_s",.05);
   return a*(-smoothValue(elapsed/q)+smoothValue((elapsed-q)/q)
          +smoothValue((elapsed-2*q)/q)-smoothValue((elapsed-3*q)/q));
  }
  return 2*smoothValue(elapsed/d("motion_ramp_s",T))*Math.sin(localPhase(time)+d("control_phase_rad",0));
 }
 void setupMotion() throws Exception {
  if(!foil||!moving)return;
  UserDefinedVertexMotion motion=s.get(MotionManager.class).createMotion(UserDefinedVertexMotion.class,"Sharp sealed flap with localized transition");
  reg.getValues().get(MotionSpecification.class).setMotion(motion);
  UserDefinedVertexMotionSolver solver=s.getSolverManager().getSolver(UserDefinedVertexMotionSolver.class);
  solver.setIgnoreGridFlux(false);
  solver.setZeroGridFlux(false);
  solver.setUpdateInnerIterations(false);
  ff("SavedCoord");
  String time=motionTime();
  String command;
  if(kinematics||b("flow_cycle")){
   double q=d("flap_quarter_s",.05); String spanTime="/<"+q+" s>";
   command=Math.toRadians(d("flap_cycle_deg",2))+"*(-"+smooth(time+spanTime)+"+"
       +smooth("("+time+"-<"+q+" s>)"+spanTime)+"+"+smooth("("+time+"-<"+(2*q)+" s>)"+spanTime)
       +"-"+smooth("("+time+"-<"+(3*q)+" s>)"+spanTime)+")";
  }else{
   double phase=localPhase(0)+d("control_phase_rad",0);
   command="0.03490658503988659*"+smooth(time+"/<"+d("motion_ramp_s",T)+" s>")+"*sin("+phase+"-<"+W+" /s>*$Time)";
  }
  if(b("af_native")) {
   UserFieldFunction commanded=s.getFieldFunctionManager().createFieldFunction();
   commanded.setFunctionName("AF_Cycle_Command");
   commanded.setDefinition("57.29577951308232*("+command+")");
  }
  String x="($$SavedCoord[0]-<"+HX+" m>)", y="($$SavedCoord[1]-<"+HY+" m>)";
  String radius="sqrt(pow("+x+",2)+pow("+y+",2))";
  String blend=smooth(x+"/<.035 m>");
  if(b("gapped_geometry")){
   String radial=smooth("(<.03755 m>-"+radius+")/<.00235 m>");
   String aft=smooth("("+x+"+<.00745 m>)/<.00745 m>");
   blend="max("+radial+","+aft+")";
  }
  String a="("+command+"*"+blend+"*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";
  UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();
  f.setFunctionName("CB_FlapTotalDisplacement");
  f.getTypeOption().setSelected(FieldFunctionTypeOption.Type.VECTOR);
  Dimensions length=new Dimensions();
  length.setLength(1);
  f.setDimensions(length);
  f.setDefinition("["+x+"*(cos("+a+")-1)+"+y+"*sin("+a+"),-"+x+"*sin("+a+")+"+y+"*(cos("+a+")-1),<0 m>]");
  reg.getConditions().get(MovingVertexOption.class).setSelected(MovingVertexOption.Type.TOTAL_DISPLACEMENT);
  VertexDisplacementProfile profile=reg.getValues().get(VertexDisplacementProfile.class);
  profile.setTotalDisplacement(true);
  vf(profile,f);
  vertices=s.getTableManager().createTable(XyzInternalTable.class);
  vertices.setPresentationName("CB Actual flap vertices");
  vertices.getParts().setObjects(walls);
  vertices.setExtractVertexData(true);
  FieldFunction position=ff("Position");
  vertices.setFieldFunctions(List.of(position.getComponentFunction(0),position.getComponentFunction(1),position.getComponentFunction(2)));
  double[] tip=sampleTip(0);
  referenceTipX=tip[0]-HX;
  referenceTipY=tip[1]-HY;
  previousAngle=0;
  previousTime=start;
 }
 double[] sampleTip(int step) throws Exception {
  Path file=kinematics||step==0?out.resolve(String.format(Locale.ROOT,"vertices_%04d.csv",step)):out.resolve("latest_vertices.csv");
  vertices.extract();
  vertices.export(file.toString(),",");
  double best=0, px=0,py=0;
  try(BufferedReader rows=Files.newBufferedReader(file)){
   String header=rows.readLine();
   if(header==null||!header.startsWith("\"Position[X]"))throw new IllegalStateException("Invalid native vertex coordinate schema");
   for(String row;(row=rows.readLine())!=null;){
    String[] c=row.split(",");
    double x=Double.parseDouble(c[0]), y=Double.parseDouble(c[1]);
    if(x<1.15)continue;
    double r=Math.hypot(x-HX,y-HY);
    if(r>best){best=r;px=x;py=y;}
   }
  }
  if(best<.23||best>.25)throw new IllegalStateException("Invalid measured trailing-edge radius "+best);
  return new double[]{px,py};
 }
 double measuredAngle(int step) throws Exception {
  if(!moving)return 0;
  double[] tip=sampleTip(step);
  double x=tip[0]-HX,y=tip[1]-HY;
  if(Math.abs(Math.hypot(x,y)-Math.hypot(referenceTipX,referenceTipY))>1e-6)
   throw new IllegalStateException("Trailing-edge rigid radius changed");
  return -Math.toDegrees(Math.atan2(referenceTipX*y-referenceTipY*x,referenceTipX*x+referenceTipY*y));
 }
 void kinematicRun() throws Exception {
  for(Solver solver:s.getSolverManager().getObjects()){
   if(!(solver instanceof UserDefinedVertexMotionSolver)&&!(solver instanceof ImplicitUnsteadySolver))solver.setFrozen(true);
  }
  save("START");
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("motion.csv"))){
   h.write("time_s,delta_command_deg,delta_measured_deg,delta_dot_rad_s,min_volume_m3,min_face_validity,min_cell_quality,solver_s\n");
   for(int step=1;step<=40;step++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";break;}
    status("RUNNING","MOTION_ONLY");
    long began=System.nanoTime();
    s.getSimulationIterator().step(1);
    double seconds=(System.nanoTime()-began)/1e9,t=s.getSolution().getPhysicalTime();
    done=step;
    if(Math.abs(t-(start+dt*step))>1e-8)throw new IllegalStateException("Kinematic timestep mismatch");
    double a=measuredAngle(step), volume=v("volume"), face=v("face"), quality=v("quality");
    h.write(t+","+targetAngle(t)+","+a+","+Math.toRadians((a-previousAngle)/(t-previousTime))+","+volume+","+face+","+quality+","+seconds+"\n");
    h.flush();
    previousAngle=a;
    previousTime=t;
    if(!(volume>0&&face>=.5&&quality>0)||Math.abs(a-targetAngle(t))>.08){
     result="HOLD_MOTION_GEOMETRY";
     break;
    }
   }
  }
  if(done==40&&result.equals("HOLD_NOT_RUN"))result="MOTION_NATIVE_PENDING_VERTEX_REVIEW";
  save("FINAL");
  write("SOLVE_STATUS.json",Map.of("status",result,"steps",done,"time_s",s.getSolution().getPhysicalTime(),
        "frozen_flow",true,"training_approved",false));
  status("STOPPED",result);
 }



 
 static final double FLAP_LIMIT=12339.214766776897;
 String gapPressureFailure(double cells,double wall,double flap,double gap){
  if(!Double.isFinite(cells+wall+flap+gap)||Math.max(cells,wall)>=1e9)
   return "HOLD_AFT_PRESSURE_READBACK";
  if(!b("pressure_diagnostic_only")&&flap<=FLAP_LIMIT)return "HOLD_FLAP_PRESSURE_MARGIN";
  return "";
 }
 boolean prepareCoarseSteady(double speed)throws Exception{
  SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);
  flow.getVelocitySolver().setUrf(.3);
  flow.getPressureSolver().setUrf(.05);
  for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())c.setIsUsed(false);
  if(!b("gap_resume_steady"))s.getSolution().initializeSolution();
  double qs=.5*1000*speed*speed*1.19;
  int rampIterations=i("steady_ramp_iterations",0);
  double u0=d("u_initial_m_s",speed);
  double[][] force=new double[i("steady_max_iterations",rampIterations==0?400:550)][3];
  result="HOLD_STEADY_NOT_SETTLED";
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("steady_history.csv"))){
   h.write("iteration,CL,CD,Mh,pABS_aft_cells_Pa,pABS_aft_wall_Pa,mass_relative,quality,U_m_s,pmin_x_m,pmin_y_m,pwall_x_m,pwall_y_m,pflap_Pa,pgap_Pa\n");
   for(int n=0;n<force.length;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";return false;}
    if(n%10==0)status("RUNNING","STEADY_SINGLE_PHASE");
    double speedNow=speed;
    if(rampIterations>0){
     speedNow=u0+(speed-u0)*smoothValue((n+1.)/rampIterations);
     inlet.getValues().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(speedNow,0,0);
    }
    s.getSimulationIterator().step(1);
    double p=v("aftcells"),pb=v("aftwall"),pflap=v("gapflap"),pgap=v("gappocket");
    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);
    if(n%5!=4&&pressureFailure.isEmpty())continue;
    double m=Math.abs(v("net")/v("influx")),q=v("quality");
    force[n]=new double[]{v("Fz")/qs,v("Fx")/qs,v("Mh")};
    h.write((n+1)+","+force[n][0]+","+force[n][1]+","+force[n][2]+","+p+","+pb+","+m+","+q+","+speedNow+","+loc("aftcells",0)+","+loc("aftcells",1)+","+loc("aftwall",0)+","+loc("aftwall",1)+","+pflap+","+pgap+"\n");h.flush();
    if(!pressureFailure.isEmpty()){result=pressureFailure;return false;}
    if(!Double.isFinite(m+q)){result="HOLD_STEADY_MESH_OR_TURBULENCE";return false;}
    if(q<=0||v("volume")<=0||v("face")<.5||v("kmin")<=1.0001e-10||v("omin")<=1.0001e-10||v("nut")>=99999){
     result="HOLD_STEADY_MESH_OR_TURBULENCE";return false;
    }
    if(n>=Math.max(149,rampIterations+99)&&n%25==24&&m<=1e-4){
     boolean stable=true;
     for(int j=0;j<3;j++){
      double a=0,c=0;
      for(int k=0;k<5;k++){a+=force[n-5*k][j];c+=force[n-25-5*k][j];}
      stable &= Math.abs(a-c)<=.07*Math.max(5e-4,Math.abs(a));
     }
     if(stable)return true;
    }
   }
  }
  return false;
 }
 void exportGapYplus(int step) throws Exception {
  for(Boundary wall:walls){
   String name=wall.getPresentationName().contains("flap")?"flap":"main";
   String label="Gap Wall Yplus "+name;
   XyzInternalTable table=s.getTableManager().getObjects().stream().filter(o->o instanceof XyzInternalTable&&o.getPresentationName().equals(label)).map(o->(XyzInternalTable)o).findFirst().orElse(null);
   if(table==null){
    table=s.getTableManager().createTable(XyzInternalTable.class);
    table.setPresentationName(label);
    table.getParts().setObjects(wall);
    table.setFieldFunctions(List.of(ff("WallYplus")));
   }
   table.extract();
   table.export(out.resolve(String.format(Locale.ROOT,"yplus_%04d_%s.csv",step,name)).toString(),",");
  }
 }

 double fixedMean(double[][] data,int end,int count,int index){
  double sum=0;for(int j=end-count;j<end;j++)sum+=data[j][index];return sum/count;
 }
 String fixedProtocol(double speed)throws Exception{
  double cap=d("fixed_cap_s",1.);
  int window=(int)Math.round(.05/dt), max=(int)Math.round(cap/dt), consecutive=0;
  if(Math.abs(window*dt-.05)>1e-9||Math.abs(max*dt-cap)>1e-9)
   throw new IllegalStateException("Fixed protocol requires exact 0.05 s windows");
  double[][] data=new double[max][2];
  double qs=.5*1000*speed*speed*1.19, origin=s.getSolution().getPhysicalTime();
  boolean restored=b("restore_fixed_history");
  int first=restored?(int)Math.round(origin/dt):0;
  if(restored&&(first<=0||first>=max||Math.abs(first*dt-origin)>1e-8))
   throw new IllegalStateException("Fixed restart time does not match a complete window");
  save("FIXED_START");
  if(restored)exportGapYplus(first);
  String stopReason="HOLD_FIXED_NOT_SETTLED";
  try(BufferedWriter hist=Files.newBufferedWriter(out.resolve("fixed_history.csv"));
      BufferedWriter windows=Files.newBufferedWriter(out.resolve("fixed_windows.csv"))){
   hist.write("physical_time_s,step,CL,CD,Fx_N,Fz_N,Mh_Nm,pflap_Pa,pgap_Pa,paft_wall_Pa,paft_cells_Pa,CFL,mass_relative,min_volume,face_validity,quality,k_min,omega_min,mut_mu_max,solver_s\n");
   windows.write("physical_time_s,step,CL_mean,CD_mean,CL_drift_fraction,CD_drift_fraction,CL_range_fraction,CD_range_fraction,consecutive_pass\n");
   if(restored){
    Path prefix=Path.of(cfg.getProperty("fixed_prefix_directory"));
    int count=0;
    try(BufferedReader old=Files.newBufferedReader(prefix.resolve("fixed_history.csv"))){
     old.readLine();
     for(String row;(row=old.readLine())!=null&&count<first;){
      String[] c=row.split(",");
      if(Integer.parseInt(c[1])!=count+1||Math.abs(Double.parseDouble(c[0])-(count+1)*dt)>1e-8)
       throw new IllegalStateException("Fixed history is discontinuous before checkpoint");
      data[count++]=new double[]{Double.parseDouble(c[2]),Double.parseDouble(c[3])};
      hist.write(row+"\n");
     }
    }
    if(count!=first)throw new IllegalStateException("Fixed history stops before checkpoint");
    int lastWindow=0;
    try(BufferedReader old=Files.newBufferedReader(prefix.resolve("fixed_windows.csv"))){
     old.readLine();
     for(String row;(row=old.readLine())!=null;){
      String[] c=row.split(",");
      int step=Integer.parseInt(c[1]);
      if(step>first)break;
      windows.write(row+"\n");lastWindow=step;consecutive=Integer.parseInt(c[8]);
     }
    }
    if(lastWindow!=(first/window)*window)throw new IllegalStateException("Missing stability window at checkpoint");
    hist.flush();windows.flush();
   }
   for(int n=first+1;n<=max;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){stopReason="HOLD_STOP_OR_DEADLINE";break;}
    status("RUNNING","FIXED_0DEG_STABILIZATION");
    long began=System.nanoTime();
    s.getSimulationIterator().step(1);
    double elapsed=(System.nanoTime()-began)/1e9,t=s.getSolution().getPhysicalTime();
    if(Math.abs(t-origin-(n-first)*dt)>1e-8)throw new IllegalStateException("Fixed timestep mismatch");
    double fx=v("Fx"),fz=v("Fz"),mh=v("Mh"),cl=fz/qs,cd=fx/qs,flap=v("gapflap"),gap=v("gappocket"),
      wall=v("aftwall"),cells=v("aftcells"),cfl=v("CFL"),mass=Math.abs(v("net")/v("influx")),
      vol=v("volume"),face=v("face"),quality=v("quality"),k=v("kmin"),omega=v("omin"),nut=v("nut");
    data[n-1]=new double[]{cl,cd};
    hist.write(t+","+n+","+cl+","+cd+","+fx+","+fz+","+mh+","+flap+","+gap+","+wall+","+cells+","+cfl+","+mass+","+vol+","+face+","+quality+","+k+","+omega+","+nut+","+elapsed+"\n");
    hist.flush();
    String pressure=gapPressureFailure(cells,wall,flap,gap);
    if(!pressure.isEmpty()){stopReason=pressure;break;}
    if(!(Double.isFinite(cl+cd+mh+cfl+mass+vol+face+quality+k+omega+nut)&&cfl<=25&&
       (n<=5||mass<=1e-4)&&vol>0&&face>=.5&&quality>0&&k>1.0001e-10&&omega>1.0001e-10&&nut<99999)){
     stopReason=cfl>25?"HOLD_FIXED_CFL":"HOLD_FIXED_NUMERICAL";break;
    }
    if(n>=2*window&&n%window==0){
     double[] avg=new double[2],drift=new double[2],range=new double[2];
     for(int i=0;i<2;i++){
      avg[i]=fixedMean(data,n,window,i);
      double previous=fixedMean(data,n-window,window,i),lo=Double.POSITIVE_INFINITY,hi=Double.NEGATIVE_INFINITY;
      for(int j=n-window;j<n;j++){lo=Math.min(lo,data[j][i]);hi=Math.max(hi,data[j][i]);}
      double scale=Math.max(Math.abs(avg[i]),1e-10);
      drift[i]=Math.abs(avg[i]-previous)/scale;range[i]=(hi-lo)/scale;
     }
     boolean ok=drift[0]<.005&&drift[1]<.005&&range[0]<.01&&range[1]<.02;
     consecutive=ok?consecutive+1:0;
     windows.write(t+","+n+","+avg[0]+","+avg[1]+","+drift[0]+","+drift[1]+","+range[0]+","+range[1]+","+consecutive+"\n");windows.flush();
     write("FIXED_PROGRESS.json",Map.of("time_s",t,"step",n,"CL_mean",avg[0],"CD_mean",avg[1],
       "CL_drift_fraction",drift[0],"CD_drift_fraction",drift[1],"consecutive",consecutive));
     if(n>=4*window&&consecutive>=3){
      exportGapYplus(n);
      save("FIXED_STABLE");
      write("FIXED_PROTOCOL.json",Map.of("status","PASS_FIXED_STABILIZATION","time_s",t,"step",n,
       "CL_mean",avg[0],"CD_mean",avg[1],"CL_drift_fraction",drift[0],"CD_drift_fraction",drift[1],
       "CL_range_fraction",range[0],"CD_range_fraction",range[1],"window_s",.05));
      return "PASS_FIXED_STABILIZATION";
     }
    }
    if(n%window==0)save(String.format(Locale.ROOT,"FIXED_STEP%04d",n));
   }
  }
  write("FIXED_PROTOCOL.json",Map.of("status",stopReason,"time_s",s.getSolution().getPhysicalTime()));
  return stopReason;
 }

 void singlePhaseRun() throws Exception {
  boolean seeded=b("seeded_single_phase"), coarse=b("coarse_2d_active"), resume=b("resume_coarse_active");
  if((!b("fresh")&&!seeded&&!resume)||!foil||!moving||kinematics||s.getNumberOfGpgpus()!=0)
   throw new IllegalStateException("Single-phase diagnostic contract");
  double speed=d("u_diagnostic_m_s",10),u0=d("u_initial_m_s",speed),rampTime=d("u_ramp_s",0),refSpan=(seeded||coarse)?1:.02;
  if(!seeded&&!resume){
  s.getImportManager().importMeshFiles(cfg.getProperty("mesh"));
  reg=s.getRegionManager().getRegions().iterator().next();
  long nc=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
  if(nc!=i("expected_cells",44442))throw new IllegalStateException("Unexpected diagnostic mesh");
  pc=s.getContinuumManager().createContinuum(PhysicsContinuum.class);
  pc.setPresentationName(coarse?"True 2D water SST active flap":"Quasi-2D single-phase URANS motion diagnostic");
  if(coarse){pc.enable(TwoDimensionalModel.class);pc.enable(SteadyModel.class);}
  else{pc.enable(ThreeDimensionalModel.class);pc.enable(ImplicitUnsteadyModel.class);}
  pc.enable(SingleComponentLiquidModel.class);
  pc.enable(SegregatedFlowModel.class);
  pc.enable(ConstantDensityModel.class);
  pc.enable(TurbulentModel.class);
  pc.enable(RansTurbulenceModel.class);
  pc.enable(KOmegaTurbulence.class);
  pc.enable(SstKwTurbModel.class);
  pc.enable(KwAllYplusWallTreatment.class);
  Material water=pc.getModelManager().getModel(SingleComponentLiquidModel.class).getMaterial();
  water.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).setConstant(1000);
  water.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).setConstant(.001);
  pc.getReferenceValues().get(ReferencePressure.class).setValue(120736.226);

  UserFieldFunction inletVelocity=null;
  if(rampTime>0){
   inletVelocity=s.getFieldFunctionManager().createFieldFunction();
   inletVelocity.setFunctionName("CB_SinglePhaseInletRamp");
   inletVelocity.getTypeOption().setSelected(FieldFunctionTypeOption.Type.VECTOR);
   Dimensions units=new Dimensions();units.setLength(1);units.setTime(-1);inletVelocity.setDimensions(units);
   inletVelocity.setDefinition("[<"+u0+" m/s>+<"+(speed-u0)+" m/s>*"+smooth("$Time/<"+rampTime+" s>")+",<0 m/s>,<0 m/s>]");
  }
  pc.getInitialConditions().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(u0,0,0);
  if(b("target_ambient_turbulence")){
   double targetK=1.5*Math.pow(.001*speed,2),targetOmega=1000*targetK/(10*.001);
   pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
   scalar(pc.getInitialConditions().get(TurbulentKineticEnergyProfile.class),targetK);
   scalar(pc.getInitialConditions().get(SpecificDissipationRateProfile.class),targetOmega);
   write("B_AMBIENT_SST.json",Map.of("k_m2_s2",targetK,"omega_s_inv",targetOmega,"reference_U_m_s",speed,"TI",.001,"viscosity_ratio",10));
  }else{
  pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);
  scalar(pc.getInitialConditions().get(TurbulenceIntensityProfile.class),.001);
  scalar(pc.getInitialConditions().get(TurbulentViscosityRatioProfile.class),10);
  }
  reg.setPhysicsContinuum(pc);
  for(Boundary bb:reg.getBoundaryManager().getBoundaries()){
   String name=bb.getPresentationName();
   if(name.contains("inlet")){
    inlet=bb;outer.add(bb);
    bb.setBoundaryType(InletBoundary.class);
    bb.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);
    if(inletVelocity!=null)vf(bb.getValues().get(VelocityProfile.class),inletVelocity);else bb.getValues().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(u0,0,0);
    if(b("target_ambient_turbulence")){
     double targetK=1.5*Math.pow(.001*speed,2);
     bb.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.K_OMEGA);
     scalar(bb.getValues().get(TurbulentKineticEnergyProfile.class),targetK);
     scalar(bb.getValues().get(SpecificDissipationRateProfile.class),1000*targetK/(10*.001));
    }else{
    bb.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);
    scalar(bb.getValues().get(TurbulenceIntensityProfile.class),.001);
    scalar(bb.getValues().get(TurbulentViscosityRatioProfile.class),10);
    }
   }else if(name.contains("outlet")){
    outer.add(bb);bb.setBoundaryType(PressureBoundary.class);scalar(bb.getValues().get(StaticPressureProfile.class),0);
   }else if(name.contains("main")||name.contains("flap")){
    bb.setBoundaryType(WallBoundary.class);walls.add(bb);if(name.contains("flap"))flaps.add(bb);
   }else{
    bb.setBoundaryType(SymmetryBoundary.class);
   }
  }
  }else{
   reg=s.getRegionManager().getRegions().iterator().next();
   pc=reg.getPhysicsContinuum();
   if(pc.getModelManager().hasModel(TwoDimensionalModel.class)==null||
      pc.getModelManager().hasModel(KwAllYplusWallTreatment.class)==null||
      pc.getModelManager().hasModel(SstKwTurbModel.class)==null)
    throw new IllegalStateException("Unexpected saved 2D SST setup");
   if(resume){
    long nc=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
    if(nc!=i("expected_cells",13597)||Math.abs(s.getSolution().getPhysicalTime()-d("expected_time",-1))>1e-10
       ||pc.getModelManager().hasModel(ImplicitUnsteadyModel.class)==null)
     throw new IllegalStateException("Active restart identity mismatch");
   }else{
    if(((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()!=i("expected_cells",-1)
       ||Math.abs(s.getSolution().getPhysicalTime()-d("expected_time",-1))>1e-10
       ||(b("fixed_from_unsteady")?pc.getModelManager().hasModel(ImplicitUnsteadyModel.class)==null:
          pc.getModelManager().hasModel(SteadyModel.class)==null))
     throw new IllegalStateException("Unexpected saved fixed checkpoint");
    if(!b("gap_resume_steady")&&!b("fixed_from_unsteady")){
     pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));
     pc.enable(ImplicitUnsteadyModel.class);
    }
   }
   for(Boundary bb:reg.getBoundaryManager().getBoundaries()){
    String n=bb.getPresentationName();
    if(n.contains("inlet")){inlet=bb;outer.add(bb);}
    else if(n.contains("outlet"))outer.add(bb);
    else if(n.contains("main")||n.contains("flap")){walls.add(bb);if(n.contains("flap"))flaps.add(bb);}
   }
   write("SEEDED_READBACK.json",Map.of("cells",((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount(),
       "initialization_called",false,"source_sim",s.getSessionPath(),"VOF",false,"span_reference_m",refSpan));
  }
  if(walls.size()!=2||flaps.size()!=1)throw new IllegalStateException("Foil labels incomplete");
  pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().setSelected(FlowUpwindOption.Type.SECOND_ORDER);
  pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().setSelected(UpwindOption.Type.SECOND_ORDER);
  List<Region> parts=List.of(reg);
  UserFieldFunction aftPressure=s.getFieldFunctionManager().createFieldFunction();
  aftPressure.setFunctionName("ExploratoryAftAbsolutePressure");
  Dimensions pressureUnits=new Dimensions();
  pressureUnits.setMass(1);pressureUnits.setLength(-1);pressureUnits.setTime(-2);
  aftPressure.setDimensions(pressureUnits);
  aftPressure.setDefinition("(($$Position[0]>=<0.7933333333333333 m>) && ($$Position[0]<=<1.29 m>) && (abs($$Position[1]-<.02128173276777 m>)<=<.15 m>)) ? $AbsolutePressure : <1e9 Pa>");
  for(MinReport pressure:List.of(min("aftcells",aftPressure,parts),min("aftwall",aftPressure,walls)))
   pressure.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1)));
  write("PRESSURE_SCOPE.json",Map.of("fidelity","EXPLORATORY_SINGLE_PHASE","x_min_m",.7933333333333333,
      "x_max_m",1.29,"y_center_m",HY,"half_height_m",.15,"hinge_radius_m",.043,
      "limit_Pa",b("pressure_diagnostic_only")?2339.214766776897:FLAP_LIMIT,
      "gate_surface",b("pressure_diagnostic_only")?"flap_wall_and_hinge_diagnostic":"flap_wall_only","full_foil_cavitation_assessment",false,"training_approved",false));
  min("gapflap",ff("AbsolutePressure"),flaps);
  UserFieldFunction hingeRadius=s.getFieldFunctionManager().createFieldFunction();
  hingeRadius.setFunctionName("GapHingeRadiusNormalized");
  hingeRadius.setDefinition("sqrt(pow(($$Position[0]-<.952 m>)/<.043 m>,2)+pow(($$Position[1]-<.02128173276777 m>)/<.043 m>,2))");
  ThresholdPart hingePocket=s.getPartManager().createThresholdPart();
  hingePocket.setPresentationName("Exploratory hinge pocket, radius 43 mm");
  hingePocket.getInputParts().setObjects(reg);
  hingePocket.setFieldFunction(hingeRadius);
  hingePocket.setRange(new DoubleVector(new double[]{0,1}));
  hingePocket.setMode(ThresholdMode.BETWEEN_TAG);
  min("gappocket",ff("AbsolutePressure"),List.of(hingePocket));
  min("quality",ff((seeded||coarse)?"LeastSquaresQuality":"CellQuality"),parts);min("volume",ff("Volume"),parts);min("face",ff("FaceValidity"),parts);
  min("kmin",ff("TurbulentKineticEnergy"),parts);min("omin",ff("SpecificDissipationRate"),parts);
  max("nut",ff("TurbulentViscosityRatio"),parts);
  MassFlowReport net=s.getReportManager().createReport(MassFlowReport.class);
  net.getParts().setObjects(outer);rep.put("net",net);
  MassFlowReport influx=s.getReportManager().createReport(MassFlowReport.class);
  influx.getParts().setObjects(inlet);rep.put("influx",influx);
  VolumeIntegralReport mass=s.getReportManager().createReport(VolumeIntegralReport.class);
  mass.setFieldFunction(ff("Density"));mass.getParts().setObjects(reg);rep.put("mass",mass);
  for(int axis=0;axis<2;axis++){
   ForceReport force=s.getReportManager().createReport(ForceReport.class);
   force.getDirection().setComponents(axis==0?1:0,axis==1?1:0,0);
   force.setPressureOption(FluidLoadsReportPressureOption.SP_UC);
   force.getParts().setObjects(walls);rep.put(axis==0?"Fx":"Fz",force);
  }
  MomentReport moment=s.getReportManager().createReport(MomentReport.class);
  moment.getDirection().setComponents(0,0,-1);moment.getOrigin().setComponents(HX,HY,(seeded||coarse)?0:.01);
  moment.setPressureOption(FluidLoadsReportPressureOption.SP_UC);
  moment.getParts().setObjects(flaps);rep.put("Mh",moment);
  write("MOMENT_CONVENTION.json",Map.of("axis_star",List.of(0,0,-1),"origin_star_m",List.of(HX,HY,.01),
     "moment_unit",(seeded||coarse)?"Nm per 1 m 2D reference span":"Nm over the 20 mm span","flap_only",true,"sign","Positive fluid torque acts towards positive trailing-edge-down deflection",
     "power","Signed fluid power = Mh * angular speed in rad/s","force_normalization_N",.5*1000*speed*speed*1.19*refSpan));
  if(coarse&&!resume&&(!seeded||b("gap_resume_steady"))){
   if(!prepareCoarseSteady(speed)){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s\n");
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status",result,"steps",0,"time_s",0,"U_m_s",speed));
    status("STOPPED",result);
    return;
   }
   if(b("gap_baseline_only")){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s"+System.lineSeparator());
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status","GAP_BASELINE_READY","steps",0,"time_s",0,"U_m_s",speed));
    status("STOPPED","GAP_BASELINE_READY");
    return;
   }
   pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));
   pc.enable(ImplicitUnsteadyModel.class);
  }
  ImplicitUnsteadySolver solver=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
  solver.getTimeStep().setValue(dt);
  solver.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
  for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){
   c.setIsUsed(c instanceof InnerIterationStoppingCriterion);
   if(c instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(inner);
  }
  s.getSimulationIterator().getAutoSave().setEnabled(false);
  if(!seeded&&!coarse&&!resume)s.getSolution().initializeSolution();
  start=s.getSolution().getPhysicalTime();
  if(b("fixed_protocol")){
   max("CFL",ff("CourantNumber"),parts);
   result=fixedProtocol(speed);
   if(!result.equals("PASS_FIXED_STABILIZATION")||!b("after_fixed_motion")){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s"+System.lineSeparator());
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status",result,"steps",0,"time_s",s.getSolution().getPhysicalTime(),"U_m_s",speed));
    status("STOPPED",result);
    return;
   }
   start=s.getSolution().getPhysicalTime();
  }
  if(resume){
   vertices=(XyzInternalTable)s.getTableManager().getTable("CB Actual flap vertices");
   if(vertices==null||s.getSolverManager().getSolver(UserDefinedVertexMotionSolver.class)==null)
    throw new IllegalStateException("Missing saved active motion");
   referenceTipX=d("reference_tip_x_m",0)-HX;referenceTipY=d("reference_tip_y_m",0)-HY;
   previousTime=start;previousAngle=measuredAngle(0);
   if(Math.abs(previousAngle-targetAngle(start))>1e-7)throw new IllegalStateException("Saved active angle mismatch");
   write("ACTIVE_RESTART_READBACK.json",Map.of("time_s",start,"angle_deg",previousAngle,
     "reinitialized",false,"motion_recreated",false));
  }else setupMotion();
  MaxReport spCfl=max("CFL",ff("CourantNumber"),parts);
  spCfl.setCollocatedFieldFunctions(List.of(ff("Position").getComponentFunction(0),ff("Position").getComponentFunction(1)));
  save("START");
  double previousMass=v("mass"), beforeMass=previousMass, peakFinal=0, qs=.5*1000*speed*speed*1.19*refSpan;
  result="PASS_DIAGNOSTIC_SMOKE";
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("single_phase.csv"));
      BufferedWriter warnings=Files.newBufferedWriter(out.resolve("PRESSURE_BELOW_VAPOR.csv"));
      BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"))){
   warnings.write("time_s,flap_Pa,hinge_Pa,vapor_pressure_Pa\n");
   h.write("time_s,solver_s,delta_command_deg,delta_measured_deg,delta_dot_rad_s,CL,CD,Fx_N,Fz_N,Mh_Nm,hinge_power_fluid_W,pABS_aft_cells_Pa,pABS_aft_wall_Pa,max_CFL,mass_relative,volume_min,face_validity,quality,k_min,omega_min,mut_mu_max,inlet_target_m_s,cfl_x_m,cfl_y_m,pflap_min_Pa,pgap_min_Pa,flap_vapor_margin_Pa\n");
   rr.write("time_s,monitor,normalized,inner_count,first,last,reduction\n");
   Map<ResidualMonitor,Integer> before=new LinkedHashMap<>();
   for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r)before.put(r,r.getAllYValues().length);
   int total=b("fixed_protocol")?(int)Math.round(.2/dt):i("steps",40);for(int step=1;step<=total;step++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";break;}
    status("RUNNING","SINGLE_PHASE_MOTION");
    long clock=System.nanoTime();
    s.getSimulationIterator().step(1);
    double sec=(System.nanoTime()-clock)/1e9;solveSeconds+=sec;
    double t=s.getSolution().getPhysicalTime();
    done=step;
    if(Math.abs(t-(start+step*dt))>1e-8)throw new IllegalStateException("Time step mismatch");
    for(var entry:before.entrySet()){
     ResidualMonitor r=entry.getKey();double[] y=r.getAllYValues();
     int n=y.length-entry.getValue();
     entry.setValue(y.length);
     if(n<=0)throw new IllegalStateException("Missing inner iterations");
     double first=y[y.length-n],last=y[y.length-1];
     rr.write(t+","+r.getPresentationName()+","+r.isNormalized()+","+n+","+first+","+last+","+Math.abs(last)/Math.max(1e-300,Math.abs(first))+"\n");
     if(step>total-25)peakFinal=Math.max(peakFinal,r.isNormalized()?Math.abs(last):Double.POSITIVE_INFINITY);
    }
    rr.flush();
    double angle=t>=d("motion_start_delay_s",0)?measuredAngle(step):0,rate=Math.toRadians((angle-previousAngle)/(t-previousTime));
    previousAngle=angle;previousTime=t;
    double mt=v("mass"),bal=Math.abs((step>1?(3*mt-4*previousMass+beforeMass)/(2*dt):(mt-previousMass)/dt)+v("net"))/Math.abs(v("influx"));
    beforeMass=previousMass;previousMass=mt;
    double fx=v("Fx"),fz=v("Fz"),mh=v("Mh"),p=v("aftcells"),pb=v("aftwall"),cfl=v("CFL"),vol=v("volume"),face=v("face"),q=v("quality");
    double pflap=v("gapflap"),pgap=v("gappocket");
    String pressureFailure=gapPressureFailure(p,pb,pflap,pgap);
    double vapor=2339.214766776897;
    if(b("pressure_diagnostic_only")&&(pflap<=vapor||pgap<=vapor)){
     warnings.write(t+","+pflap+","+pgap+","+vapor+"\n");warnings.flush();
    }
    h.write(t+","+sec+","+targetAngle(t)+","+angle+","+rate+","+fz/qs+","+fx/qs+","+fx+","+fz+","+mh+","+mh*rate+","+p+","+pb+","+cfl+","+bal+","+vol+","+face+","+q+","+v("kmin")+","+v("omin")+","+v("nut")+","+(rampTime>0?u0+(speed-u0)*smoothValue(t/rampTime):speed)+","+maxLoc("CFL",0)+","+maxLoc("CFL",1)+","+pflap+","+pgap+","+(pflap-2339.214766776897)+"\n");
    h.flush();
    if(step==1||step==total||Math.abs(t-start-.05)<1e-8||Math.abs(t-start-.15)<1e-8) exportGapYplus(step);
    int physicalIndex=(int)Math.round(t/dt);
    if(coarse&&(physicalIndex%50==0||step==total))Files.copy(out.resolve("latest_vertices.csv"),out.resolve(String.format(Locale.ROOT,"vertices_step%04d.csv",physicalIndex)));
    if(!pressureFailure.isEmpty()){result=pressureFailure;break;}
    if(!(cfl<=25&&Double.isFinite(bal)
         &&(step<=5||bal<=1e-4)&&vol>0&&face>=.5&&q>0&&v("kmin")>1.0001e-10&&v("omin")>1.0001e-10
         &&v("nut")<99999&&Double.isFinite(fx)&&Double.isFinite(fz)&&Double.isFinite(mh)&&Math.abs(angle-targetAngle(t))<=.08)){
     result="HOLD_SINGLE_PHASE_SAFETY";break;
    }
    if(step%200==0&&step<total)save(String.format(Locale.ROOT,"ACTIVE_STEP%04d",step));
   }
  }
  if(result.equals("PASS_DIAGNOSTIC_SMOKE")&&!coarse&&(!Double.isFinite(peakFinal)||peakFinal>.01))
   result="HOLD_RESIDUAL_WINDOW";
  sampleTip(0+100000);Files.copy(out.resolve("latest_vertices.csv"),out.resolve("vertices_final.csv"));
  save("FINAL");
  write("SOLVE_STATUS.json",Map.of("status",result,"steps",done,"time_s",s.getSolution().getPhysicalTime(),
        "normalized_max_final25",peakFinal,"U_m_s",speed,"VOF",false,"training_approved",false));
  status("STOPPED",result);
 }







 SolutionHistory playbackHistory;
 RecordedSolutionView playbackView;
 Scene playbackPressure, playbackSpeed, playbackStreams;
 int playbackStep=-1;
 boolean playbackDisabled=false;

 Scene playbackScene(String name){
  Scene sc=s.getSceneManager().createScene(name);
  sc.initializeAndWait();
  sc.getCurrentView().setInput(new DoubleVector(new double[]{.80,.03,.01}),
      new DoubleVector(new double[]{.80,.03,3}),new DoubleVector(new double[]{0,1,0}),
      .38,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);
  return sc;
 }

 void playbackWalls(Scene sc){
  PartDisplayer pd=sc.getDisplayerManager().createPartDisplayer("Recorded hydrofoil walls");
  pd.getInputParts().setObjects(walls);pd.setRepresentation(playbackView.getRepresentation());
  pd.setOutline(true);pd.setMesh(true);pd.setLineWidth(2);
 }

 void beginPlayback(Path file)throws Exception{
  if(Files.exists(file))throw new IllegalStateException("History file already exists");
  if(Files.getFileStore(file.getParent()).getUsableSpace()<4L*1024*1024*1024)
   throw new IllegalStateException("Insufficient space for VOF history");
  PlaneSection plane=s.getPartManager().createPlaneSection();
  plane.setPresentationName("AF - VOF midspan section");
  plane.getInputParts().setObjects(reg);
  plane.setOrigin(new DoubleVector(new double[]{0,0,.01}));
  plane.setOrientation(new DoubleVector(new double[]{0,0,1}));
  playbackHistory=s.get(SolutionHistoryManager.class).createForFile(file.toString(),false);
  playbackHistory.setPresentationName("AF - Calm VOF dynamic flap history");
  playbackHistory.setAutoRecord(false);playbackHistory.setAutoRescan(true);
  playbackHistory.getRegions().setObjects(reg);
  List<NamedObject> inputs=new ArrayList<>();inputs.add(plane);inputs.addAll(walls);
  playbackHistory.getInputs().setObjects(inputs);
  playbackHistory.setFunctions(List.of(ff("AbsolutePressure"),ff("Velocity"),ff("Velocity").getMagnitudeFunction(),ff("VolumeFractionwater")));
  recordPlayback(0);
  playbackView=playbackHistory.createRecordedSolutionView();
  playbackView.setPresentationName("AF - VOF playback");
  playbackView.setStateIndex(playbackHistory.getMinStateIndex());

  playbackWalls(playbackScene("AF VOF 01 - Recorded foil geometry"));
  Scene meshScene=playbackScene("AF VOF 06 - Recorded mesh");
  PartDisplayer cells=meshScene.getDisplayerManager().createPartDisplayer("Recorded cross-section mesh");
  cells.getInputParts().setObjects(plane);cells.setRepresentation(playbackView.getRepresentation());
  cells.setMesh(true);cells.setOutline(true);playbackWalls(meshScene);

  playbackPressure=playbackScene("AF VOF 02 - Recorded absolute pressure");
  ScalarDisplayer pressure=playbackPressure.getDisplayerManager().createScalarDisplayer("Absolute pressure");
  pressure.getInputParts().setObjects(plane);pressure.setRepresentation(playbackView.getRepresentation());
  pressure.getScalarDisplayQuantity().setFieldFunction(ff("AbsolutePressure"));
  pressure.getScalarDisplayQuantity().setRangeMin(-60000);pressure.getScalarDisplayQuantity().setRangeMax(220000);
  playbackWalls(playbackPressure);

  Scene speed=playbackSpeed=playbackScene("AF VOF 03 - Recorded velocity magnitude");
  ScalarDisplayer v=speed.getDisplayerManager().createScalarDisplayer("Speed");
  v.getInputParts().setObjects(plane);v.setRepresentation(playbackView.getRepresentation());
  v.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
  v.getScalarDisplayQuantity().setRangeMin(0);v.getScalarDisplayQuantity().setRangeMax(30);
  playbackWalls(speed);

  Scene streams=playbackStreams=playbackScene("AF VOF 04 - Recorded streamlines");
  StreamPart stream=s.getPartManager().createStreamPart();
  stream.setPresentationName("AF - VOF upstream streamline seeds");stream.getInputParts().setObjects(reg);
  stream.setFieldFunction(ff("Velocity"));stream.setMode(SeedMode.LINE);
  stream.getLineSeed().setPoint1(new DoubleVector(new double[]{-.35,-.25,.01}));
  stream.getLineSeed().setPoint2(new DoubleVector(new double[]{-.35,.28,.01}));
  stream.getLineSeed().setResolution(45);stream.getIntegrator().setMaximumNumberOfSteps(2500);
  stream.getIntegrator().setDirection(IntegrationDirection.FORWARD);
  StreamDisplayer sd=streams.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
  sd.getInputParts().setObjects(stream);sd.setRepresentation(playbackView.getRepresentation());
  sd.setMode(StreamDisplayerMode.LINES);sd.setColorMode(StreamColorMode.SCALAR);
  sd.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
  sd.getScalarDisplayQuantity().setRangeMin(0);sd.getScalarDisplayQuantity().setRangeMax(30);
  playbackWalls(streams);
  write("AF_VOF_PLAYBACK_SETUP.json",Map.of("history",file.toString(),"capture_stride_steps",25,"frame_interval_s",.005,
       "geometry","recorded mesh plus foil walls","fields",List.of("AbsolutePressure","Velocity","VolumeFractionwater"),
       "view","AF - VOF playback","scenes",4));
 }

 void recordPlayback(int step)throws Exception{
  if(playbackHistory==null||playbackDisabled||step==playbackStep)return;
  if(Files.getFileStore(playbackHistory.getPath().toPath().getParent()).getUsableSpace()<2L*1024*1024*1024)
   throw new IllegalStateException("Insufficient disk space for next VOF history frame");
  playbackHistory.createSnapshot(String.format(Locale.ROOT,"step_%05d_t%.6f",step,s.getSolution().getPhysicalTime()));
  playbackStep=step;
  write("AF_VOF_PLAYBACK_PROGRESS.json",Map.of("history",playbackHistory.getPath().toString(),
       "states",playbackHistory.getNumberOfStates(),"last_step",step,"last_time_s",s.getSolution().getPhysicalTime()));
 }

 void safelyRecordPlayback(int step)throws Exception{
  try{recordPlayback(step);}
  catch(Exception failure){
   playbackDisabled=true;
   write("AF_VOF_PLAYBACK_WARNING.json",Map.of("step",step,"error",failure.toString(),"CFD_continues",true));
  }
 }
 public void execute(){s=getActiveSimulation();out=Paths.get(System.getenv("MINI_CASE_DIR"));try{
  try(Reader r=Files.newBufferedReader(out.resolve("job.properties"))){cfg.load(r);}if(!Set.of("COMEBACK_DAY_20261104","COMEBACK_NIGHT_APPROVED").contains(cfg.getProperty("authorization","")))throw new IllegalStateException("Explicit stage authorization required");dt=d("dt",.001);inner=i("inner",20);foil=b("foil");moving=b("moving");kinematics=b("kinematics");amp=d("amplitude",.05);oldAmp=d("old_amplitude",amp);ramp=d("ramp_s",0);deadline=Long.parseLong(cfg.getProperty("deadline_ms"));stop=Paths.get(cfg.getProperty("stop_path"));if(b("single_phase")){singlePhaseRun();return;}configure();reports();if(moving)setupMotion();
  if(b("af_native")){
   if(b("native_remesh_initialize")){
    for(Scene old:s.getSceneManager().getScenes())
     if(old.getPresentationName().startsWith("AF FIXED"))old.setPresentationName("Previous mesh - "+old.getPresentationName());
   }
   String previousHistory=cfg.getProperty("source_af_history","");
   if(!previousHistory.isBlank()){
    Path src=Paths.get(previousHistory);
    if(!Files.isRegularFile(src)||!src.getFileName().toString().endsWith(".simh"))throw new IllegalStateException("AF restart history missing");
    SolutionHistory h=s.get(SolutionHistoryManager.class).getSolutionHistory("AF - Solution History");
    Path local=out.resolve(h.getPath().toPath()).normalize();
    if(!local.getParent().equals(out.normalize())||!local.getFileName().equals(src.getFileName()))
     throw new IllegalStateException("AF history would write outside the owned run: "+local);
    Files.copy(src,local);
    h.rescanFile();
    if(h.getNumberOfStates()<1)throw new IllegalStateException("AF restart history did not load");
    int archivedFrames=h.getNumberOfStates();
    h.setAutoRecord(false);
    h.setAutoRescan(false);
    if(b("af_branch_history")){
     RecordedSolutionView view=null;
     for(var item:s.get(SolutionViewManager.class).getObjects())
      if(item instanceof RecordedSolutionView v&&v.getSolutionHistory().equals(h)&&v.getPresentationName().equals("AF - Playback"))view=v;
     if(view==null)throw new IllegalStateException("AF playback view missing");
     Path fresh=out.resolve(out.getFileName()+"_AF_resume.simh");
     SolutionHistory next=s.get(SolutionHistoryManager.class).createForFile(fresh.toString(),false);
     next.setAutoRecord(false);next.setAutoRescan(false);
     next.getRegions().setObjects(reg);next.getInputs().setObjects(h.getInputs().getObjects());
     next.setFunctions(h.getFunctions());
     next.createSnapshot(String.format(Locale.ROOT,"AF_resume_t%.6f",s.getSolution().getPhysicalTime()));
     Representation previousRep=view.getRepresentation();
     h.setPresentationName("Archived AF history "+out.getFileName());
     next.setPresentationName("AF - Solution History");
     view.setSolutionHistory(next);view.setStateIndex(next.getMinStateIndex());
     Representation nextRep=view.getRepresentation();
     for(Scene scene:s.getSceneManager().getScenes())
      if(scene.getPresentationName().startsWith("AF FIXED "))
       for(var pd:scene.getDisplayerManager().getObjects())
        if(previousRep.equals(pd.getRepresentation()))pd.setRepresentation(nextRep);
     next.getStarUpdateStageable().getStarUpdate().setUpdateMode(StarUpdate.TIMESTEP);
     next.getStarUpdateStageable().getStarUpdate().setUpdateFrequency(25);
     next.setAutoRecord(true);
     write("AF_RESUME_HISTORY.json",Map.of("path",fresh.toString(),"archive_path",local.toString(),"archived_frames",archivedFrames,
      "states_before_solve",next.getNumberOfStates(),"auto_record",next.getAutoRecord(),"auto_rescan",next.getAutoRescan()));
    }else{
     write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",archivedFrames,"auto_record",false));
    }
   }
   new AfNativeOutput().install(s,reg,walls,flaps,out,moving,!previousHistory.isBlank());

   double cl=(v("Fz")-9810*(11.2-v("fluidVolume")))/3855.6, cd=v("Fx")/3855.6;
   double liveCl=s.getReportManager().getReport("AF_CL").getReportMonitorValue();
   double liveCd=s.getReportManager().getReport("AF_CD").getReportMonitorValue();
   if(!Double.isFinite(liveCl+liveCd)||Math.abs(liveCl-cl)>1e-7||Math.abs(liveCd-cd)>1e-7)
    throw new IllegalStateException("AF native reports do not match solver CL/CD");
  }
  if(moving&&b("calm_active_pilot")){
   Path archive=Paths.get("T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104/FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST");
   beginPlayback(archive.resolve(out.getFileName()+"_AF_VOF_playback.simh"));
  }
  write("BUILD_STATUS.json",Map.of("status","BUILT_NOT_SOLVED","cells",((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()));
  if(v("quality")<=0||v("volume")<=0||v("face")<.5)throw new IllegalStateException("Initial native mesh quality failure");if(foil&&b("fresh")&&!kinematics&&amp==0)write("CALM_HYDROSTATIC_READBACK.json",Map.of("Fz_total_initial_N",v("Fz"),"reference_buoyancy_N",d("buoyancy_reference_N",22.717957840926616),"Mh_initial_Nm",v("Mh"),"note","Initial flat-surface hydrostatic field with uniform free stream; compare magnitude and sign before using buoyancy correction"));if(b("report_probe")){save("REPORT_PROBE");write("SOLVE_STATUS.json",Map.of("status","REPORT_PROBE_PASS","steps",0,"time_s",start,"gauges",gauges.size()));return;}if(kinematics){kinematicRun();return;}save("START");fields.extract();fields.export(out.resolve("field_start.csv").toString(),",");if(!cfg.getProperty("flow_seed","").isBlank()){double pStart=v("pmin");write("FLOW_SEED_NATIVE_READBACK.json",Map.of("pABSmin_Pa",pStart,"maximum_speed_m_s",v("vmax")));if(!(pStart>12339.214766776897)||!(v("vmax")>18&&v("vmax")<40))throw new IllegalStateException("Initial V2 seed native field check failed");}
  if(b("calm_only")&&(b("fresh")||b("c01_seeded")||b("native_remesh_initialize")))auditHydrostatics();if(b("c01_seeded")||(b("clean_calm")&&b("fresh"))||b("native_remesh_initialize"))auditRecoveryStart();
  ArrayList<Double> liftHistory=new ArrayList<>(),dragHistory=new ArrayList<>();
  int stableWindows=i("fixed_stable_count",0);
  boolean fixedHistorySeeded=false;
  if(b("matched_calm_fixed")&&!cfg.getProperty("fixed_window_seed","").isBlank()){
   int window=(int)Math.round(.05/dt);
   List<String> rows=Files.readAllLines(Paths.get(cfg.getProperty("fixed_window_seed")));
   int seedSize=rows.size()-1;
   if(seedSize<1||seedSize>=2*window||!rows.get(0).equals("time_s,CL,CD"))throw new IllegalStateException("Fixed history seed schema mismatch");
   for(int k=1;k<rows.size();k++){
    String[] row=rows.get(k).split(",");
    double t=Double.parseDouble(row[0]),cl=Double.parseDouble(row[1]),cd=Double.parseDouble(row[2]);
    if(Math.abs(t-(start-(seedSize-k)*dt))>1e-9||!Double.isFinite(cl+cd))
     throw new IllegalStateException("Fixed history seed time or force mismatch");
    liftHistory.add(cl);dragHistory.add(cd);
   }
   fixedHistorySeeded=true;
  }
  writeResidualFactors("RESIDUAL_FACTORS_START.json");double prev=v("mass"),prev2=prev;ArrayList<Map<String,Double>>ends=new ArrayList<>();double saveInterval=d("save_interval_s",T),nextSave=start+saveInterval;long wall=System.nanoTime();result="NUMERICAL_END_REVIEW";
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("history.csv"));BufferedWriter g=Files.newBufferedWriter(out.resolve("gauges.csv"));BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"));BufferedWriter ab=Files.newBufferedWriter(out.resolve("gauges_absorption.csv"));BufferedWriter timing=Files.newBufferedWriter(out.resolve("step_wall.csv"));BufferedWriter warnings=Files.newBufferedWriter(out.resolve("PRESSURE_BELOW_VAPOR.csv"))){
   warnings.write("time_s,domain_Pa,foil_Pa,flap_Pa,vapor_pressure_Pa\n");
   h.write("time_s,step,solver_s,pABSmin_Pa,pmin_x,pmin_y,pmin_z,interface_CFL,max_CFL,alpha_min,alpha_max,mass_kg,net_flux_kg_s,mass_relative,k_min,omega_min,nut_ratio_max,vmax,vz_absmax,quality,volume_min,face_validity,Ux,Uy,Ux_theory,Uy_theory,phase_rad,amplitude_target,CL,CD,Fx,Fz,Mh,Mh_per_m,pbody,pflap,pbody_x,pbody_y,yplus_min,yplus_max,yplus_mean,delta_command_deg,delta_measured_deg,delta_dot_rad_s,hinge_power_fluid_W,Fz_reference_buoyancy_corrected_N,phase_analytic_at_foil_rad,Fz_hydrostatic_displaced_water_N,Fz_minus_geometry_buoyancy_N,interface_CFL_global_upper_bound,Fx_pressure_N,Fx_viscous_N,vmax_x_m,vmax_y_m,vmax_z_m\n");g.write("time_s,x_m,eta_actual_m,eta_native_theory_m\n");ab.write("time_s,x_m,eta_actual_m,eta_native_theory_m\n");timing.write("time_s,step_wall_s\n");rr.write("time_s,monitor,normalized,inner_count,first,last,reduction,min_inner,max_inner\n");
   for(int step=1;step<=i("steps",40);step++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";break;}status("RUNNING","SOLVING");Map<ResidualMonitor,Integer>before=new LinkedHashMap<>();for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor)before.put((ResidualMonitor)m,((ResidualMonitor)m).getAllYValues().length);
    long began=System.nanoTime();s.getSimulationIterator().step(1);double sec=(System.nanoTime()-began)/1e9;solveSeconds+=sec;done=step;double t=s.getSolution().getPhysicalTime();if(Math.abs(t-(start+step*dt))>1e-8)throw new IllegalStateException("Physical time reset or wrong step size");
    Map<String,Double>end=new LinkedHashMap<>();for(ResidualMonitor m:before.keySet()){double[]y=m.getAllYValues();int n=y.length-before.get(m);if(n<=0)throw new IllegalStateException("Residual history not progressing");double first=y[y.length-n],last=y[y.length-1],lo=Double.POSITIVE_INFINITY,hi=0;for(int j=y.length-n;j<y.length;j++){lo=Math.min(lo,Math.abs(y[j]));hi=Math.max(hi,Math.abs(y[j]));}rr.write(t+","+m.getPresentationName()+","+m.isNormalized()+","+n+","+first+","+last+","+(Math.abs(last)/Math.max(1e-300,Math.abs(first)))+","+lo+","+hi+"\n");end.put(m.getPresentationName(),m.isNormalized()?Math.abs(last):Double.POSITIVE_INFINITY);}rr.flush();ends.add(end);
    if(step==1){double period=nativePeriod();write("STOKES_AFTER_FIRST_STEP.json",Map.of("native_period_s",period,"time_s",t));if(!moving&&Double.isFinite(period)&&period>.40&&period<.52){T=period;W=2*Math.PI/T;}}
    double mass=v("mass"),net=v("net"),bal=Math.abs((step>1?(3*mass-4*prev+prev2)/(2*dt):(mass-prev)/dt)+net)/Math.abs(v("influx"));prev2=prev;prev=mass;double fx=foil?v("Fx"):Double.NaN,fz=foil?v("Fz"):Double.NaN,mh=foil?v("Mh"):Double.NaN,cl=foil?(fz-d("buoyancy_reference_N",22.717957840926616))/3855.6:Double.NaN,cd=foil?fx/3855.6:Double.NaN;
    double hydro=foil?9810*(11.2-v("fluidVolume")):Double.NaN;
    if(foil&&b("matched_calm"))cl=(fz-hydro)/3855.6;
    double actual=measuredAngle(step), rate=moving?Math.toRadians((actual-previousAngle)/(t-previousTime)):0;previousAngle=actual;previousTime=t;
    if(b("pressure_diagnostic_only")){
     double vapor=2339.214766776897, pDomain=v("pmin"),pFoil=v("pbody"),pFlap=v("pflap");
     if(Math.min(pDomain,Math.min(pFoil,pFlap))<=vapor){
      warnings.write(t+","+pDomain+","+pFoil+","+pFlap+","+vapor+"\n");warnings.flush();
     }
    }
    flatCflFallback=false;
    h.write(t+","+step+","+sec+","+v("pmin")+","+loc("pmin",0)+","+loc("pmin",1)+","+loc("pmin",2)+","+v("interfaceCFL")+","+v("CFL")+","+v("alphaMin")+","+v("alphaMax")+","+mass+","+net+","+bal+","+v("kmin")+","+v("omin")+","+v("nut")+","+v("vmax")+","+Math.max(Math.abs(v("vzmax")),Math.abs(v("vzmin")))+","+v("quality")+","+v("volume")+","+v("face")+","+v("ux")+","+v("uy")+","+v("ut")+","+v("vt")+","+(2*Math.PI*t/T)+","+amp+","+cl+","+cd+","+fx+","+fz+","+mh+","+(mh/span)+","+(foil?v("pbody"):Double.NaN)+","+(foil?v("pflap"):Double.NaN)+","+(foil?loc("pbody",0):Double.NaN)+","+(foil?loc("pbody",1):Double.NaN)+","+(foil?v("ymin"):Double.NaN)+","+(foil?v("ymax"):Double.NaN)+","+(foil?v("ymean"):Double.NaN)+","+targetAngle(t)+","+actual+","+rate+","+(mh*rate)+","+(fz-d("buoyancy_reference_N",22.717957840926616))+","+localPhase(t)+","+hydro+","+(fz-hydro)+","+flatCflFallback+","+(foil?v("FxPressure"):Double.NaN)+","+(foil?v("FxShear"):Double.NaN)+","+maxLoc("vmax",0)+","+maxLoc("vmax",1)+","+maxLoc("vmax",2)+"\n");h.flush();double maxEta=0;
    for(int n=0;n<xs.length;n++){
     double area=moving?areaReports.get(n).getReportMonitorValue():gaugeAreas.get(n);
     double eta=(gauges.get(n).getReportMonitorValue()-area)/span+4-sy;
     (xs[n]>=20?ab:g).write(t+","+xs[n]+","+eta+","+((theory.get(n).getReportMonitorValue()-area)/span+4-sy)+"\n");
     maxEta=Math.max(maxEta,Math.abs(eta));
    }
    g.flush();ab.flush();timing.write(t+","+((System.nanoTime()-began)/1e9)+"\n");timing.flush();
    if(playbackHistory!=null&&step%25==0)safelyRecordPlayback(step);
    if(b("af_native")&&(step==1||step%25==0)){
     Map<String,Object> samples=new LinkedHashMap<>();
     for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ReportMonitor rm&&m.getPresentationName().startsWith("AF_")){
      double[] values=rm.getAllYValues();
      samples.put(m.getPresentationName(),Map.of("count",values.length,"last",values.length==0?Double.NaN:values[values.length-1]));
     }
     Map<String,Object> historyCounts=new LinkedHashMap<>();
     for(SolutionHistory history:s.get(SolutionHistoryManager.class).getObjects()){
      if(history.getPresentationName().equals("AF - Solution History")&&b("af_branch_history"))history.rescanFile();
      if(history.getPresentationName().startsWith("AF - "))historyCounts.put(history.getPresentationName(),history.getNumberOfStates());
     }
     write("AF_NATIVE_SAMPLES.json",Map.of("time_s",t,"step",step,"monitors",samples,"history_states",historyCounts,
       "report_CL",cl,"report_CD",cd,"actual_flap_deg",actual));
     if(step==1)save("AF_FIRST_STEP");
    }

    String bad=moving&&Math.abs(actual-targetAngle(t))>.08?"MOTION_TRACKING":maxEta>.375?"INTERFACE_REFINEMENT_BAND":physical(step,bal);
    if(!bad.isEmpty()){result="HOLD_"+bad;reason=bad;break;}if(t>=nextSave-1e-9){save(String.format(Locale.US,"CP_%06d_t%.6f",step,t));nextSave+=saveInterval;}
    if(b("matched_calm_fixed")){
     liftHistory.add(cl);dragHistory.add(cd);
     int n=liftHistory.size(),w=(int)Math.round(.05/dt);
     if(n>=2*w&&n%w==0&&i("fixed_elapsed_before",0)+step>=4*w){
      double[] stats=new double[6];
      var series=List.of(liftHistory,dragHistory);
      for(int j=0;j<2;j++){
       var a=series.get(j);double mean=0,previous=0,low=Double.POSITIVE_INFINITY,high=Double.NEGATIVE_INFINITY;
       for(int k=n-w;k<n;k++){double value=a.get(k);mean+=value;previous+=a.get(k-w);low=Math.min(low,value);high=Math.max(high,value);}
       mean/=w;previous/=w;stats[j]=mean;stats[j+2]=Math.abs(mean-previous)/Math.max(1e-12,Math.abs(previous));
       stats[j+4]=(high-low)/Math.max(1e-12,Math.abs(mean));
      }
      stableWindows=stats[2]<.005&&stats[3]<.005&&stats[4]<.01&&stats[5]<.02?stableWindows+1:0;
      write("CALM_FIXED_PROGRESS.json",Map.of("time_s",t,"stable_windows",stableWindows,"CL",stats[0],"CD",stats[1],
        "CL_drift_fraction",stats[2],"CD_drift_fraction",stats[3],"CL_range_fraction",stats[4],"CD_range_fraction",stats[5]));
      if(stableWindows==3){result="PASS_CALM_FORCE_STABILIZATION";break;}
     }
    }
    if((System.nanoTime()-wall)/1e9>d("wall_budget_s",18000)){result="HOLD_WALL_BUDGET";break;}
   }
  }
  if(playbackHistory!=null)safelyRecordPlayback(done);
  if(b("native_remesh_initialize")){
   for(SolutionHistory h:s.get(SolutionHistoryManager.class).getObjects()){
    if(!h.getPresentationName().endsWith(out.getFileName().toString()))continue;
    h.createSnapshot(String.format(Locale.ROOT,"AF_fixed_final_%05d",done));
    write("AF_PLAYBACK_FINAL.json",Map.of("states",h.getNumberOfStates(),"history_file",h.getPath().toString(),
     "time_s",s.getSolution().getPhysicalTime(),"scenes",List.of("mesh","speed","pressure","streamlines","water","foil")));
    try{
     RecordedSolutionView last=null;
     for(var item:s.get(SolutionViewManager.class).getObjects())
      if(item instanceof RecordedSolutionView view&&view.getPresentationName().endsWith(out.getFileName().toString()))last=view;
     if(last==null)throw new IllegalStateException("Final recorded solution view missing");
     last.setStateIndex(h.getMaxStateIndex());
     Representation active=last.getRepresentation();
     Map<String,Object> evidence=new LinkedHashMap<>();
     for(Scene sc:s.getSceneManager().getScenes()){
      String name=sc.getPresentationName();
      if(!name.startsWith("AF FIXED")||name.contains("01 -")||name.contains("05 -"))continue;
      String key=name.contains("06 -")?"mesh":name.contains("02 -")?"pressure":name.contains("03 -")?"velocity":"streamlines";
      long assigned=sc.getDisplayerManager().getObjects().stream()
        .filter(displayer->active.equals(displayer.getRepresentation())).count();
      evidence.put(key,Map.of("scene",name,"displayers_on_recorded_view",assigned));
      sc.printAndWait(out.resolve("AF_RECORDED_"+key+".png").toString(),1,1100,650);
     }
     write("AF_PLAYBACK_SCENES.json",evidence);
    }catch(Exception e){write("AF_PLAYBACK_PREVIEW_WARNING.json",Map.of("error",e.toString()));}

   }
  }

  boolean residual=ends.size()>=25;Map<String,Object>gate=new LinkedHashMap<>();if(ends.size()>0)for(String n:ends.get(ends.size()-1).keySet()){double mx=0;for(int q=Math.max(0,ends.size()-25);q<ends.size();q++)mx=Math.max(mx,ends.get(q).get(n));gate.put(n,mx);residual&=mx<=.01;}writeResidualFactors("RESIDUAL_FACTORS_END.json");write("RESIDUAL_FINAL25.json",Map.of("maxima",gate,"normalized_limit",.01,"count",Math.min(25,ends.size()),"pass",residual));if(result.equals("NUMERICAL_END_REVIEW"))result=b("matched_calm_fixed")?"HOLD_CALM_FORCE_DRIFT":residual?"NUMERICAL_END_PASS":"HOLD_RESIDUAL_WINDOW";
  write("STOKES_AFTER_FINAL_STEP.json",Map.of("native_period_s",nativePeriod(),"height_m",waveHeight(),"time_s",s.getSolution().getPhysicalTime()));fields.extract();fields.export(out.resolve("field_end.csv").toString(),",");save("FINAL");if(foil&&wallTable!=null){wallTable.extract();wallTable.export(out.resolve("wall_yplus_pressure.csv").toString(),",");}for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor)m.export(out.resolve("residual_"+m.getPresentationName().replaceAll("[^A-Za-z0-9]","_")+".csv").toString());write("SOLVE_STATUS.json",Map.of("status",result,"reason",reason,"steps",done,"time_s",s.getSolution().getPhysicalTime(),"solver_seconds",solveSeconds,"residual_pass",residual,"foil",foil,"amplitude_target",amp,"training_approved",false));status("STOPPED",result);
 }catch(Exception e){e.printStackTrace(System.err);try{write("ERROR.json",Map.of("error",e.toString(),"steps",done,"time_s",s.getSolution().getPhysicalTime()));if(!s.getRegionManager().getRegions().isEmpty())save("ERROR_CHECKPOINT");write("SOLVE_STATUS.json",Map.of("status","HOLD_ERROR","error",e.toString(),"steps",done,"time_s",s.getSolution().getPhysicalTime()));status("STOPPED","HOLD_ERROR");}catch(Exception ignored){}throw new RuntimeException(e);}finally{if("1".equals(System.getenv("COMEBACK_OWN_SESSION")))try{s.close(ServerConnection.CloseOption.Close);}catch(Exception closeError){closeError.printStackTrace(System.err);}}}
}






class AfNativeOutput {
  Simulation s;
  Path out;
  Region region;
  List<Boundary> walls = new ArrayList<>(), flap = new ArrayList<>();
  Map<String,ReportMonitor> monitors = new LinkedHashMap<>();
  final double hx=.952, hy=.02128173276777;
  void install(Simulation sim, Region r, List<Boundary> body, List<Boundary> flaps, Path folder, boolean moving, boolean keepHistory) throws Exception {
    s=sim;region=r;walls=body;flap=flaps;out=folder;
    if(s.getReportManager().getObjects().stream().anyMatch(rep->rep.getPresentationName().equals("AF_CL"))){
      for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ReportMonitor rm && m.getPresentationName().startsWith("AF_"))
        monitors.put(rm.getReport().getPresentationName(),rm);
    }else reports(false);
    for(SolutionHistory previous:s.get(SolutionHistoryManager.class).getObjects()){
      if(previous.getPresentationName().startsWith("AF - Fixed VOF Solution History")){
        previous.setAutoRecord(false);
        previous.setAutoRescan(false);
      }
    }
    if(moving) {
      ((ExpressionReport)monitors.get("AF_Delta_Command_deg").getReport()).setDefinition("$AF_Cycle_Command");
      UserFieldFunction angle=s.getFieldFunctionManager().createFieldFunction();
      angle.setFunctionName("AF_Aft_Mesh_Angle");
      String x="($$SavedCoord[0]-<.952 m>)", y="($$SavedCoord[1]-<.02128173276777 m>)";
      String px="($$Position[0]-<.952 m>)", py="($$Position[1]-<.02128173276777 m>)";
      angle.setDefinition("("+x+"><.20 m>) ? -57.29577951308232*atan(("+x+"*"+py+"-"+y+"*"+px+")/("+x+"*"+px+"+"+y+"*"+py+")) : -999");
      MaxReport measured=s.getReportManager().createReport(MaxReport.class);
      measured.setPresentationName("AF_Mesh_Angle");measured.setSmooth(false);
      measured.setFieldFunction(angle);measured.getParts().setObjects(flap);
      ((ExpressionReport)monitors.get("AF_Delta_Measured_deg").getReport()).setDefinition("${AF_Mesh_AngleReport}");
      plot("AF 07 - Lift coefficient vs measured flap deflection [deg]",monitors.get("AF_Delta_Measured_deg"),"AF_CL");
      plot("AF 08 - Drag coefficient vs measured flap deflection [deg]",monitors.get("AF_Delta_Measured_deg"),"AF_CD");
    }else if(!keepHistory)history();
    Files.writeString(out.resolve("AF_NATIVE_READY.txt"),"reports="+monitors.keySet()+"\nCL="+monitors.get("AF_CL").getReport().getReportMonitorValue()+"\nCD="+monitors.get("AF_CD").getReport().getReportMonitorValue()+"\n");
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
    Path path=out.resolve(out.getFileName()+"_AF_Fixed.simh");
    if(Files.exists(path))throw new IllegalStateException("AF history exists");
    PlaneSection plane=s.getPartManager().createPlaneSection();
    plane.setPresentationName("AF fixed - Midspan section");
    plane.getInputParts().setObjects(region);plane.setOrigin(v(0,0,.01));plane.setOrientation(v(0,0,1));
    SolutionHistory h=s.get(SolutionHistoryManager.class).createForFile(path.toString(),false);
    h.setPresentationName("AF - Fixed VOF Solution History " + out.getFileName());
    h.setAutoRecord(false);h.setAutoRescan(true);
    h.getRegions().setObjects(region);
    List<NamedObject> input=new ArrayList<>(walls);input.add(plane);
    h.getInputs().setObjects(input);
    h.setFunctions(List.of(ff("AbsolutePressure"),ff("Velocity"),ff("Velocity").getMagnitudeFunction(),ff("VolumeFractionwater")));
    h.createSnapshot("AF_fixed_checkpoint");
    RecordedSolutionView view=h.createRecordedSolutionView();
    view.setPresentationName("AF - Fixed VOF playback " + out.getFileName());view.setStateIndex(h.getMinStateIndex());
    Representation rep=view.getRepresentation();
    scene("AF FIXED 01 - Recorded foil geometry",rep,.36);
    Scene meshScene=scene("AF FIXED 06 - Recorded mesh",rep,.45);
    PartDisplayer cells=meshScene.getDisplayerManager().createPartDisplayer("Recorded cross-section mesh");
    cells.getInputParts().setObjects(plane);cells.setRepresentation(rep);cells.setMesh(true);cells.setOutline(true);

    scalar("AF FIXED 02 - Recorded absolute pressure",rep,plane,ff("AbsolutePressure"),.36);
    scalar("AF FIXED 03 - Recorded speed",rep,plane,ff("Velocity").getMagnitudeFunction(),.36);
    Scene sc=scene("AF FIXED 04 - Recorded streamlines",rep,.51);
    StreamPart lines=s.getPartManager().createStreamPart();lines.setPresentationName("AF fixed - Upstream streamline seeds");
    lines.getInputParts().setObjects(region);lines.setFieldFunction(ff("Velocity"));lines.setMode(SeedMode.LINE);
    lines.getLineSeed().setPoint1(v(-.38,-.38,.01));lines.getLineSeed().setPoint2(v(-.38,.42,.01));lines.getLineSeed().setResolution(51);
    StreamDisplayer sd=sc.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
    sd.getInputParts().setObjects(lines);sd.setRepresentation(rep);sd.setMode(StreamDisplayerMode.LINES);
    sd.setColorMode(StreamColorMode.SCALAR);sd.getScalarDisplayQuantity().setFieldFunction(ff("Velocity").getMagnitudeFunction());
    scalar("AF FIXED 05 - Recorded water volume fraction",rep,plane,ff("VolumeFractionwater"),2.6);
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

