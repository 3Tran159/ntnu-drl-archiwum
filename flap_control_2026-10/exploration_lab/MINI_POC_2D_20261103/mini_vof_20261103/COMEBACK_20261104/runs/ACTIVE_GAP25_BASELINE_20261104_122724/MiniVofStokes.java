package macro;
import star.motion.*;import star.common.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.material.*;import star.segregatedflow.*;import star.turbulence.*;import star.kwturb.*;import star.vof.*;import star.mixturemultiphase.*;import star.vis.*;import java.nio.file.*;import java.io.*;import java.util.*;
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

 void configure()throws Exception{
  if(b("clean_calm")&&(!b("calm_only")||moving||kinematics||amp!=0||oldAmp!=0
     ||d("calm_speed_ramp_s",0)!=0||b("calm_explicit_ambient")||b("c01_seeded")
     ||!cfg.getProperty("flow_seed","").isBlank()))throw new IllegalStateException("Clean CALM requires native fields and no imposed forcing");
  if(!b("fresh")){reg=s.getRegionManager().getRegions().iterator().next();pc=reg.getPhysicsContinuum();double expected=d("expected_time",-1);if(Math.abs(s.getSolution().getPhysicalTime()-expected)>1e-9)throw new IllegalStateException("Input physical time mismatch");VofWaveModel vm=pc.getModelManager().getModel(VofWaveModel.class);for(ManagedVofWave w:vm.getVofWaveManager().getObjects())if(w instanceof FifthOrderVofWave){if(wave!=null)throw new IllegalStateException("Ambiguous wave");wave=(FifthOrderVofWave)w;}if(wave==null&&!b("calm_only")){if(!b("from_calm")||oldAmp!=0||ramp<=0)throw new IllegalStateException("Missing native Stokes V");createStokes(vm,0);}if(wave!=null&&b("calm_only"))throw new IllegalStateException("CALM input contains a Stokes object");}
  else fresh();
  long nc=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();if(nc!=i("expected_cells",foil?44442:41280)||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Mesh/GPU contract mismatch");
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
  if(wave==null){if(amp!=0||oldAmp!=0||moving)throw new IllegalStateException("Flat calm contract");}
  else if(Math.abs(amp-oldAmp)>1e-12){if(ramp<=0)throw new IllegalStateException("Continuous amplitude ramp required");String x="min(1.0,max(0.0,($Time-<"+d("ramp_origin_s",start)+" s>)/<"+ramp+" s>))";wave.getWaveHeight().setDefinition("<"+Math.max(1e-6,2*oldAmp)+" m>+<"+(2*amp-Math.max(1e-6,2*oldAmp))+" m>*(10*pow("+x+",3)-15*pow("+x+",4)+6*pow("+x+",5))");}else wave.getWaveHeight().setValue(Math.max(1e-6,2*amp));
  ImplicitUnsteadySolver un=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);un.getTimeStep().setValue(dt);un.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);PressureSolver ps=s.getSolverManager().getSolver(SegregatedFlowSolver.class).getPressureSolver();double oldUrf=ps.getUrf(),oldTol=ps.getAMGLinearSolver().getConvergeTol();ps.getAMGLinearSolver().setConvergeTol(d("pressure_tol",.01));ps.setUrf(d("pressure_urf",.5));
  for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){if(c instanceof PhysicalTimeStoppingCriterion||c instanceof StepStoppingCriterion)c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(inner);c.setIsUsed(true);}}
  s.getSimulationIterator().getAutoSave().setEnabled(false);if(b("fresh")){useSeededInitialFlow();s.getSolution().initializeSolution();}double nativePeriod=nativePeriod();if(Double.isFinite(nativePeriod)&&nativePeriod>.40&&nativePeriod<.52){T=nativePeriod;W=2*Math.PI/T;}write("STOKES_READBACK.json",Map.of("wave_type",wave==null?"FlatVofWave":"FifthOrderVofWave","native_period_s",nativePeriod,"period_planning_s",wave==null?0:T,"height_m",waveHeight(),"depth_m",sy+10,"wavelength_m",wave==null?0:wave.getVofWaveSpecification().getWaveLength().getSIValue(),"advancing_direction","+X","current_m_s",18,"global_initialization",b("fresh")&&oldAmp>0));
  Map<String,Object>a=new LinkedHashMap<>();a.put("stage",cfg.getProperty("stage"));a.put("clean_unforced_calm",b("clean_calm"));a.put("cells",nc);a.put("start_time",start);a.put("dt",dt);a.put("inner",inner);a.put("initialization_called",b("fresh"));a.put("calm_speed_ramp_s",d("calm_speed_ramp_s",0));a.put("explicit_ambient_k_omega",b("calm_explicit_ambient"));a.put("initial_calm_current_m_s",d("calm_speed_ramp_s",0)>0?.05:18);a.put("reset_on_loaded_fields",false);a.put("old_pressure_urf",oldUrf);a.put("pressure_urf",ps.getUrf());a.put("old_pressure_tol",oldTol);a.put("pressure_tol",ps.getAMGLinearSolver().getConvergeTol());a.put("amplitude_from",oldAmp);a.put("amplitude_target",amp);a.put("amplitude_ramp_s",ramp);a.put("initial_field",oldAmp==0?"flat water and air":"native Stokes V");a.put("inlet_ramp",ramp>0?"S5, zero endpoint first/second derivative":"Existing globally initialized wave; no velocity/amplitude jump");a.put("forcing_length_m",d("forcing_length",4));a.put("damping_length_m",d("damping_length",8));a.put("outlet_and_top","native flat-wave pressure and volume fraction");a.put("vorticity_limiter",pc.getModelManager().getModel(SstKwTurbModel.class).getKwTurbRealizabilityOption().getSelectedElement().toString());a.put("all_yplus",pc.getModelManager().hasModel(KwAllYplusWallTreatment.class)!=null);a.put("sst",pc.getModelManager().hasModel(SstKwTurbModel.class)!=null);a.put("reference_C01_CL",.3156595);a.put("reference_C01_CD",.00700232);a.put("C01_not_modified",true);write("SETUP_READBACK.json",a);
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
 String physical(int step,double bal){if(!Double.isFinite(bal)||(foil&&(!Double.isFinite(v("pbody"))||!Double.isFinite(v("pflap")))))return "NONFINITE_SAFETY_MEASUREMENT";if(v("pmin")<=12339.214766776897||(foil&&Math.min(v("pbody"),v("pflap"))<=12339.214766776897))return"PRESSURE";if(v("quality")<=0||v("volume")<=0||v("face")<.5)return"MESH";if(v("interfaceCFL")>.5||v("CFL")>25)return"CFL";if(v("alphaMin")<-.00001||v("alphaMax")>1.00001)return"ALPHA";if(v("kmin")<=1.0001e-10||v("omin")<=1.0001e-10||v("nut")>=99999)return"TURBULENCE_LIMIT";if(v("vmax")>180)return"VELOCITY";if(step>5&&bal>1e-4)return"MASS";for(String k:List.of("pmin","quality","volume","face","interfaceCFL","CFL","kmin","omin","nut","vmax"))if(!Double.isFinite(v(k)))return"NONFINITE_"+k;return"";}
 
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
   return -2*smoothValue(elapsed/.05)+2*smoothValue((elapsed-.05)/.05)
          +2*smoothValue((elapsed-.10)/.05)-2*smoothValue((elapsed-.15)/.05);
  }
  return 2*smoothValue(elapsed/d("motion_ramp_s",T))*Math.sin(localPhase(time)+d("control_phase_rad",0));
 }
 void setupMotion() throws Exception {
  if(!foil||!moving)return;
  UserDefinedVertexMotion motion=s.get(MotionManager.class).createMotion(UserDefinedVertexMotion.class,"Rigid gapped flap with local mesh deformation");
  reg.getValues().get(MotionSpecification.class).setMotion(motion);
  UserDefinedVertexMotionSolver solver=s.getSolverManager().getSolver(UserDefinedVertexMotionSolver.class);
  solver.setIgnoreGridFlux(false);
  solver.setZeroGridFlux(false);
  solver.setUpdateInnerIterations(false);
  ff("SavedCoord");
  String time=motionTime();
  String command;
  if(kinematics||b("flow_cycle")){
   command="0.03490658503988659*(-"+smooth(time+"/<.05 s>")+"+"+smooth("("+time+"-<.05 s>)/<.05 s>")
       +"+"+smooth("("+time+"-<.10 s>)/<.05 s>")+"-"+smooth("("+time+"-<.15 s>)/<.05 s>")+")";
  }else{
   double phase=localPhase(0)+d("control_phase_rad",0);
   command="0.03490658503988659*"+smooth(time+"/<"+d("motion_ramp_s",T)+" s>")+"*sin("+phase+"-<"+W+" /s>*$Time)";
  }
  String x="($$SavedCoord[0]-<"+HX+" m>)", y="($$SavedCoord[1]-<"+HY+" m>)";
  String radius="sqrt(pow("+x+",2)+pow("+y+",2))";
  String radial=smooth("(<.03755 m>-"+radius+")/<.00235 m>");
  String aft=smooth("("+x+"+<.00745 m>)/<.00745 m>");
  String a="("+command+"*max("+radial+","+aft+")*"+smooth("(<1.40 m>-"+radius+")/<1.10 m>")+")";
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



 
 boolean prepareCoarseSteady(double speed)throws Exception{
  SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);
  flow.getVelocitySolver().setUrf(.3);
  flow.getPressureSolver().setUrf(.05);
  for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())c.setIsUsed(false);
  s.getSolution().initializeSolution();
  double qs=.5*1000*speed*speed*1.19;
  double[][] force=new double[400][3];
  result="HOLD_STEADY_NOT_SETTLED";
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("steady_history.csv"))){
   h.write("iteration,CL,CD,Mh,pABSmin,pbody,mass_relative,quality\n");
   for(int n=0;n<force.length;n++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";return false;}
    if(n%10==0)status("RUNNING","STEADY_SINGLE_PHASE");
    s.getSimulationIterator().step(1);
    if(n%5!=4)continue;
    double p=v("pmin"),pb=v("pbody"),m=Math.abs(v("net")/v("influx")),q=v("quality");
    force[n]=new double[]{v("Fz")/qs,v("Fx")/qs,v("Mh")};
    h.write((n+1)+","+force[n][0]+","+force[n][1]+","+force[n][2]+","+p+","+pb+","+m+","+q+"\n");h.flush();
    if(!Double.isFinite(p+pb+m+q)||p<=12339.214766776897||pb<=12339.214766776897){
     result="HOLD_STEADY_PRESSURE";return false;
    }
    if(q<=0||v("volume")<=0||v("face")<.5||v("kmin")<=1.0001e-10||v("omin")<=1.0001e-10||v("nut")>=99999){
     result="HOLD_STEADY_MESH_OR_TURBULENCE";return false;
    }
    if(n>=149&&n%25==24&&m<=1e-4){
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
   XyzInternalTable table=(XyzInternalTable)s.getTableManager().getTable(label);
   if(table==null){
    table=s.getTableManager().createTable(XyzInternalTable.class);
    table.setPresentationName(label);
    table.getParts().setObjects(wall);
    table.setFieldFunctions(List.of(ff("WallYplus"),ff("AbsolutePressure")));
   }
   table.extract();
   table.export(out.resolve(String.format(Locale.ROOT,"yplus_%04d_%s.csv",step,name)).toString(),",");
  }
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
    pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));
    pc.enable(ImplicitUnsteadyModel.class);
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
  min("pmin",ff("AbsolutePressure"),parts);min("pbody",ff("AbsolutePressure"),walls);
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
  if(coarse&&!resume&&!seeded){
   if(!prepareCoarseSteady(speed)){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s\n");
    save("FINAL");
    write("SOLVE_STATUS.json",Map.of("status",result,"steps",0,"time_s",0,"U_m_s",speed));
    status("STOPPED",result);
    return;
   }
   if(b("gap_baseline_only")){
    Files.writeString(out.resolve("single_phase.csv"),"time_s,solver_s
");
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
      BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"))){
   h.write("time_s,solver_s,delta_command_deg,delta_measured_deg,delta_dot_rad_s,CL,CD,Fx_N,Fz_N,Mh_Nm,hinge_power_fluid_W,pABSmin_Pa,pbody_min_Pa,max_CFL,mass_relative,volume_min,face_validity,quality,k_min,omega_min,mut_mu_max,inlet_target_m_s,cfl_x_m,cfl_y_m\n");
   rr.write("time_s,monitor,normalized,inner_count,first,last,reduction\n");
   int total=i("steps",40);for(int step=1;step<=total;step++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";break;}
    status("RUNNING","SINGLE_PHASE_MOTION");
    Map<ResidualMonitor,Integer> before=new LinkedHashMap<>();
    for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r)before.put(r,r.getAllYValues().length);
    long clock=System.nanoTime();
    s.getSimulationIterator().step(1);
    double sec=(System.nanoTime()-clock)/1e9;solveSeconds+=sec;
    double t=s.getSolution().getPhysicalTime();
    done=step;
    if(Math.abs(t-(start+step*dt))>1e-8)throw new IllegalStateException("Time step mismatch");
    for(var entry:before.entrySet()){
     ResidualMonitor r=entry.getKey();double[] y=r.getAllYValues();
     int n=y.length-entry.getValue();
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
    double fx=v("Fx"),fz=v("Fz"),mh=v("Mh"),p=v("pmin"),pb=v("pbody"),cfl=v("CFL"),vol=v("volume"),face=v("face"),q=v("quality");
    h.write(t+","+sec+","+targetAngle(t)+","+angle+","+rate+","+fz/qs+","+fx/qs+","+fx+","+fz+","+mh+","+mh*rate+","+p+","+pb+","+cfl+","+bal+","+vol+","+face+","+q+","+v("kmin")+","+v("omin")+","+v("nut")+","+(rampTime>0?u0+(speed-u0)*smoothValue(t/rampTime):speed)+","+maxLoc("CFL",0)+","+maxLoc("CFL",1)+"\n");
    h.flush();
    if(step==1||step==total||Math.abs(t-.05)<1e-8||Math.abs(t-.15)<1e-8) exportGapYplus(step);
    int physicalIndex=(int)Math.round(t/dt);
    if(coarse&&(physicalIndex%50==0||step==total))Files.copy(out.resolve("latest_vertices.csv"),out.resolve(String.format(Locale.ROOT,"vertices_step%04d.csv",physicalIndex)));
    if(!(p>12339.214766776897&&pb>12339.214766776897&&cfl<=25&&Double.isFinite(bal)
         &&(step<=5||bal<=1e-4)&&vol>0&&face>=.5&&q>0&&v("kmin")>1.0001e-10&&v("omin")>1.0001e-10
         &&v("nut")<99999&&Double.isFinite(fx)&&Double.isFinite(fz)&&Double.isFinite(mh)&&Math.abs(angle-targetAngle(t))<=.08)){
     result="HOLD_SINGLE_PHASE_SAFETY";break;
    }
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






 public void execute(){s=getActiveSimulation();out=Paths.get(System.getenv("MINI_CASE_DIR"));try{
  try(Reader r=Files.newBufferedReader(out.resolve("job.properties"))){cfg.load(r);}if(!Set.of("COMEBACK_DAY_20261104","COMEBACK_NIGHT_APPROVED").contains(cfg.getProperty("authorization","")))throw new IllegalStateException("Explicit stage authorization required");dt=d("dt",.001);inner=i("inner",20);foil=b("foil");moving=b("moving");kinematics=b("kinematics");amp=d("amplitude",.05);oldAmp=d("old_amplitude",amp);ramp=d("ramp_s",0);deadline=Long.parseLong(cfg.getProperty("deadline_ms"));stop=Paths.get(cfg.getProperty("stop_path"));if(b("single_phase")){singlePhaseRun();return;}configure();reports();if(moving)setupMotion();write("BUILD_STATUS.json",Map.of("status","BUILT_NOT_SOLVED","cells",((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()));
  if(v("quality")<=0||v("volume")<=0||v("face")<.5)throw new IllegalStateException("Initial native mesh quality failure");if(foil&&b("fresh")&&!kinematics&&amp==0)write("CALM_HYDROSTATIC_READBACK.json",Map.of("Fz_total_initial_N",v("Fz"),"reference_buoyancy_N",d("buoyancy_reference_N",22.717957840926616),"Mh_initial_Nm",v("Mh"),"note","Initial flat-surface hydrostatic field with uniform free stream; compare magnitude and sign before using buoyancy correction"));if(b("report_probe")){save("REPORT_PROBE");write("SOLVE_STATUS.json",Map.of("status","REPORT_PROBE_PASS","steps",0,"time_s",start,"gauges",gauges.size()));return;}if(kinematics){kinematicRun();return;}save("START");fields.extract();fields.export(out.resolve("field_start.csv").toString(),",");if(!cfg.getProperty("flow_seed","").isBlank()){double pStart=v("pmin");write("FLOW_SEED_NATIVE_READBACK.json",Map.of("pABSmin_Pa",pStart,"maximum_speed_m_s",v("vmax")));if(!(pStart>12339.214766776897)||!(v("vmax")>18&&v("vmax")<40))throw new IllegalStateException("Initial V2 seed native field check failed");}
  if(b("calm_only")&&(b("fresh")||b("c01_seeded")))auditHydrostatics();if(b("c01_seeded")||(b("clean_calm")&&b("fresh")))auditRecoveryStart();
  writeResidualFactors("RESIDUAL_FACTORS_START.json");double prev=v("mass"),prev2=prev;ArrayList<Map<String,Double>>ends=new ArrayList<>();double saveInterval=d("save_interval_s",T),nextSave=start+saveInterval;long wall=System.nanoTime();result="NUMERICAL_END_REVIEW";
  try(BufferedWriter h=Files.newBufferedWriter(out.resolve("history.csv"));BufferedWriter g=Files.newBufferedWriter(out.resolve("gauges.csv"));BufferedWriter rr=Files.newBufferedWriter(out.resolve("residual_per_step.csv"));BufferedWriter ab=Files.newBufferedWriter(out.resolve("gauges_absorption.csv"));BufferedWriter timing=Files.newBufferedWriter(out.resolve("step_wall.csv"))){
   h.write("time_s,step,solver_s,pABSmin_Pa,pmin_x,pmin_y,pmin_z,interface_CFL,max_CFL,alpha_min,alpha_max,mass_kg,net_flux_kg_s,mass_relative,k_min,omega_min,nut_ratio_max,vmax,vz_absmax,quality,volume_min,face_validity,Ux,Uy,Ux_theory,Uy_theory,phase_rad,amplitude_target,CL,CD,Fx,Fz,Mh,Mh_per_m,pbody,pflap,pbody_x,pbody_y,yplus_min,yplus_max,yplus_mean,delta_command_deg,delta_measured_deg,delta_dot_rad_s,hinge_power_fluid_W,Fz_reference_buoyancy_corrected_N,phase_analytic_at_foil_rad,Fz_hydrostatic_displaced_water_N,Fz_minus_geometry_buoyancy_N,interface_CFL_global_upper_bound,Fx_pressure_N,Fx_viscous_N,vmax_x_m,vmax_y_m,vmax_z_m\n");g.write("time_s,x_m,eta_actual_m,eta_native_theory_m\n");ab.write("time_s,x_m,eta_actual_m,eta_native_theory_m\n");timing.write("time_s,step_wall_s\n");rr.write("time_s,monitor,normalized,inner_count,first,last,reduction,min_inner,max_inner\n");
   for(int step=1;step<=i("steps",40);step++){
    if(Files.exists(stop)||System.currentTimeMillis()>deadline){result="HOLD_STOP_OR_DEADLINE";break;}status("RUNNING","SOLVING");Map<ResidualMonitor,Integer>before=new LinkedHashMap<>();for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor)before.put((ResidualMonitor)m,((ResidualMonitor)m).getAllYValues().length);
    long began=System.nanoTime();s.getSimulationIterator().step(1);double sec=(System.nanoTime()-began)/1e9;solveSeconds+=sec;done=step;double t=s.getSolution().getPhysicalTime();if(Math.abs(t-(start+step*dt))>1e-8)throw new IllegalStateException("Physical time reset or wrong step size");
    Map<String,Double>end=new LinkedHashMap<>();for(ResidualMonitor m:before.keySet()){double[]y=m.getAllYValues();int n=y.length-before.get(m);if(n<=0)throw new IllegalStateException("Residual history not progressing");double first=y[y.length-n],last=y[y.length-1],lo=Double.POSITIVE_INFINITY,hi=0;for(int j=y.length-n;j<y.length;j++){lo=Math.min(lo,Math.abs(y[j]));hi=Math.max(hi,Math.abs(y[j]));}rr.write(t+","+m.getPresentationName()+","+m.isNormalized()+","+n+","+first+","+last+","+(Math.abs(last)/Math.max(1e-300,Math.abs(first)))+","+lo+","+hi+"\n");end.put(m.getPresentationName(),m.isNormalized()?Math.abs(last):Double.POSITIVE_INFINITY);}rr.flush();ends.add(end);
    if(step==1){double period=nativePeriod();write("STOKES_AFTER_FIRST_STEP.json",Map.of("native_period_s",period,"time_s",t));if(!moving&&Double.isFinite(period)&&period>.40&&period<.52){T=period;W=2*Math.PI/T;}}
    double mass=v("mass"),net=v("net"),bal=Math.abs((step>1?(3*mass-4*prev+prev2)/(2*dt):(mass-prev)/dt)+net)/Math.abs(v("influx"));prev2=prev;prev=mass;double fx=foil?v("Fx"):Double.NaN,fz=foil?v("Fz"):Double.NaN,mh=foil?v("Mh"):Double.NaN,cl=foil?(fz-d("buoyancy_reference_N",22.717957840926616))/3855.6:Double.NaN,cd=foil?fx/3855.6:Double.NaN;
    double hydro=foil?9810*(11.2-v("fluidVolume")):Double.NaN;
    double actual=measuredAngle(step), rate=moving?Math.toRadians((actual-previousAngle)/(t-previousTime)):0;previousAngle=actual;previousTime=t;
    flatCflFallback=false;
    h.write(t+","+step+","+sec+","+v("pmin")+","+loc("pmin",0)+","+loc("pmin",1)+","+loc("pmin",2)+","+v("interfaceCFL")+","+v("CFL")+","+v("alphaMin")+","+v("alphaMax")+","+mass+","+net+","+bal+","+v("kmin")+","+v("omin")+","+v("nut")+","+v("vmax")+","+Math.max(Math.abs(v("vzmax")),Math.abs(v("vzmin")))+","+v("quality")+","+v("volume")+","+v("face")+","+v("ux")+","+v("uy")+","+v("ut")+","+v("vt")+","+(2*Math.PI*t/T)+","+amp+","+cl+","+cd+","+fx+","+fz+","+mh+","+(mh/span)+","+(foil?v("pbody"):Double.NaN)+","+(foil?v("pflap"):Double.NaN)+","+(foil?loc("pbody",0):Double.NaN)+","+(foil?loc("pbody",1):Double.NaN)+","+(foil?v("ymin"):Double.NaN)+","+(foil?v("ymax"):Double.NaN)+","+(foil?v("ymean"):Double.NaN)+","+targetAngle(t)+","+actual+","+rate+","+(mh*rate)+","+(fz-d("buoyancy_reference_N",22.717957840926616))+","+localPhase(t)+","+hydro+","+(fz-hydro)+","+flatCflFallback+","+(foil?v("FxPressure"):Double.NaN)+","+(foil?v("FxShear"):Double.NaN)+","+maxLoc("vmax",0)+","+maxLoc("vmax",1)+","+maxLoc("vmax",2)+"\n");h.flush();double maxEta=0;
    for(int n=0;n<xs.length;n++){
     double area=moving?areaReports.get(n).getReportMonitorValue():gaugeAreas.get(n);
     double eta=(gauges.get(n).getReportMonitorValue()-area)/span+4-sy;
     (xs[n]>=20?ab:g).write(t+","+xs[n]+","+eta+","+((theory.get(n).getReportMonitorValue()-area)/span+4-sy)+"\n");
     maxEta=Math.max(maxEta,Math.abs(eta));
    }
    g.flush();ab.flush();timing.write(t+","+((System.nanoTime()-began)/1e9)+"\n");timing.flush();
    String bad=moving&&Math.abs(actual-targetAngle(t))>.08?"MOTION_TRACKING":maxEta>.375?"INTERFACE_REFINEMENT_BAND":physical(step,bal);
    if(!bad.isEmpty()){result="HOLD_"+bad;reason=bad;break;}if(t>=nextSave-1e-9){save(String.format(Locale.US,"CP_%06d_t%.6f",step,t));nextSave+=saveInterval;}
    if((System.nanoTime()-wall)/1e9>d("wall_budget_s",18000)){result="HOLD_WALL_BUDGET";break;}
   }
  }
  boolean residual=ends.size()>=25;Map<String,Object>gate=new LinkedHashMap<>();if(ends.size()>0)for(String n:ends.get(ends.size()-1).keySet()){double mx=0;for(int q=Math.max(0,ends.size()-25);q<ends.size();q++)mx=Math.max(mx,ends.get(q).get(n));gate.put(n,mx);residual&=mx<=.01;}writeResidualFactors("RESIDUAL_FACTORS_END.json");write("RESIDUAL_FINAL25.json",Map.of("maxima",gate,"normalized_limit",.01,"count",Math.min(25,ends.size()),"pass",residual));if(result.equals("NUMERICAL_END_REVIEW"))result=residual?"NUMERICAL_END_PASS":"HOLD_RESIDUAL_WINDOW";
  write("STOKES_AFTER_FINAL_STEP.json",Map.of("native_period_s",nativePeriod(),"height_m",waveHeight(),"time_s",s.getSolution().getPhysicalTime()));fields.extract();fields.export(out.resolve("field_end.csv").toString(),",");save("FINAL");if(foil&&wallTable!=null){wallTable.extract();wallTable.export(out.resolve("wall_yplus_pressure.csv").toString(),",");}for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor)m.export(out.resolve("residual_"+m.getPresentationName().replaceAll("[^A-Za-z0-9]","_")+".csv").toString());write("SOLVE_STATUS.json",Map.of("status",result,"reason",reason,"steps",done,"time_s",s.getSolution().getPhysicalTime(),"solver_seconds",solveSeconds,"residual_pass",residual,"foil",foil,"amplitude_target",amp,"training_approved",false));status("STOPPED",result);
 }catch(Exception e){e.printStackTrace(System.err);try{write("ERROR.json",Map.of("error",e.toString(),"steps",done,"time_s",s.getSolution().getPhysicalTime()));if(!s.getRegionManager().getRegions().isEmpty())save("ERROR_CHECKPOINT");write("SOLVE_STATUS.json",Map.of("status","HOLD_ERROR","error",e.toString(),"steps",done,"time_s",s.getSolution().getPhysicalTime()));status("STOPPED","HOLD_ERROR");}catch(Exception ignored){}throw new RuntimeException(e);}finally{if("1".equals(System.getenv("COMEBACK_OWN_SESSION")))try{s.close(ServerConnection.CloseOption.Close);}catch(Exception closeError){closeError.printStackTrace(System.err);}}}
}
