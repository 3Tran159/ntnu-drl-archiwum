package macro;
import star.common.*;import star.overset.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.meshing.*;import star.material.*;import star.flow.*;import star.segregatedflow.*;import star.turbulence.*;import star.kwturb.*;import star.motion.*;import star.vis.*;import star.sweptmesher.*;import star.prismmesher.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class C0SpeedDownSmoke extends StarMacro {

Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;List<Region> regions=new ArrayList<>();List<Boundary> fixed=new ArrayList<>(),flap=new ArrayList<>();double xh=.952,zh=.02128173276776986;String variant;boolean steadyResume=false;Map<Region,Motion> savedMotions=new LinkedHashMap<>();double[] savedFlapBounds;
void note(String text)throws Exception{s.println("HYDRO_STAGE "+text);Files.writeString(out.resolve("progress.txt"),text+"\n");}
void guard()throws Exception{if(Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Paused");if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("CPU-only working model");s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);}
UserFieldFunction field(String name,String definition,Dimensions dimensions){if(s.getFieldFunctionManager().hasFunction(name)){UserFieldFunction existing=(UserFieldFunction)s.getFieldFunctionManager().getFunction(name);if(!existing.getDefinition().equals(definition))throw new IllegalStateException("Existing diagnostic field changed");return existing;}UserFieldFunction f=s.getFieldFunctionManager().createFieldFunction();f.setPresentationName(name);f.setFunctionName(name);f.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);f.setDimensions(dimensions);f.setDefinition(definition);return f;}
void constant(ScalarProfile p,double v){p.setMethod(ConstantScalarProfileMethod.class);p.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValue(v);}
void velocity(VectorProfile p){p.setMethod(ConstantVectorProfileMethod.class);p.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(18,0,0);}
void pressure(ScalarProfile p,FieldFunction f){p.setMethod(FunctionScalarProfileMethod.class);p.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
void turbulence(Boundary b){b.getConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);constant(b.getValues().get(TurbulenceIntensityProfile.class),.001);constant(b.getValues().get(TurbulentViscosityRatioProfile.class),10);}
PhysicsContinuum physics(){
PhysicsContinuum pc=s.getContinuumManager().createContinuum(PhysicsContinuum.class);pc.setPresentationName("HYDRO water SST singlephase");
pc.enable(ThreeDimensionalModel.class);pc.enable(ImplicitUnsteadyModel.class);pc.enable(SingleComponentLiquidModel.class);pc.enable(SegregatedFlowModel.class);pc.enable(ConstantDensityModel.class);pc.enable(TurbulentModel.class);pc.enable(RansTurbulenceModel.class);pc.enable(KOmegaTurbulence.class);pc.enable(SstKwTurbModel.class);pc.enable(KwAllYplusWallTreatment.class);pc.enable(GravityModel.class);pc.enable(CellQualityRemediationModel.class);
Material water=pc.getModelManager().getModel(SingleComponentLiquidModel.class).getMaterial();water.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).setConstant(1000);water.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).setConstant(.001);
pc.getReferenceValues().get(ReferencePressure.class).setValue(101325);pc.getReferenceValues().get(Gravity.class).setComponents(0,0,-9.8100004196167);pc.getReferenceValues().get(ReferenceAltitude.class).setComponents(0,0,2);
velocity(pc.getInitialConditions().get(VelocityProfile.class));pc.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_VISCOSITY_RATIO);constant(pc.getInitialConditions().get(TurbulenceIntensityProfile.class),.001);constant(pc.getInitialConditions().get(TurbulentViscosityRatioProfile.class),10);
Dimensions pd=new Dimensions();pd.setPressure(1);field("HYDRO_HydrostaticGauge","<1000 kg/m^3>*<9.8100004196167 m/s^2>*(<2 m> - $$Position[2])",pd);UserFieldFunction hp=field("HYDRO_PiezometricZero","<0 Pa>",pd);pressure(pc.getInitialConditions().get(InitialPressureProfile.class),hp);
for(Region r:regions){r.setPhysicsContinuum(pc);for(Boundary b:r.getBoundaryManager().getBoundaries()){
 if(b.getBoundaryType() instanceof InletBoundary){b.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);velocity(b.getValues().get(VelocityProfile.class));turbulence(b);}
 else if(b.getBoundaryType() instanceof PressureBoundary){pressure(b.getValues().get(StaticPressureProfile.class),hp);turbulence(b);}else if(b.getBoundaryType() instanceof WallBoundary&&b.getPresentationName().endsWith("bottom")){b.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.SLIP);}
}}
ImplicitUnsteadySolver u=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);u.getTimeStep().setValue(.0004);u.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(15);}}
return pc;
}
ForceReport force(String name,double x,double y,double z,List<Boundary> bs){ForceReport f=s.getReportManager().createReport(ForceReport.class);f.setPresentationName(name);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getDirection().setComponents(x,y,z);f.getParts().setObjects(bs);f.createMonitor();return f;}
MinReport minimum(String name,String ff,Collection<? extends NamedObject> parts,boolean coordinates){MinReport r=s.getReportManager().createReport(MinReport.class);r.setPresentationName(name);r.getParts().setObjects(parts);r.setSmooth(false);if(coordinates)r.setCollocatedFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(0),s.getFieldFunctionManager().getFunction("Position").getComponentFunction(1),s.getFieldFunctionManager().getFunction("Position").getComponentFunction(2)));r.setFieldFunction(s.getFieldFunctionManager().getFunction(ff));r.createMonitor();return r;}
void reports(double buoyancy)throws Exception{
List<Boundary> all=new ArrayList<>(fixed);all.addAll(flap);force("HF_Fx_N",1,0,0,all);force("HF_Fz_N",0,0,1,all);
MomentReport m=s.getReportManager().createReport(MomentReport.class);m.setPresentationName("HF_Mh_Nm");m.setPressureOption(FluidLoadsReportPressureOption.SP_UC);m.getDirection().setComponents(0,1,0);m.getOrigin().setComponents(xh,.02,zh);m.getParts().setObjects(flap.isEmpty()?fixed:flap);m.createMonitor();
ExpressionReport cl=s.getReportManager().createReport(ExpressionReport.class);cl.setPresentationName("HF_CL_hydro");cl.setDefinition("($"+"{HF_Fz_NReport} - <"+buoyancy+" N>)/<3855.6 N>");cl.createMonitor();
ExpressionReport cd=s.getReportManager().createReport(ExpressionReport.class);cd.setPresentationName("HF_CD");cd.setDefinition("$"+"{HF_Fx_NReport}/<3855.6 N>");cd.createMonitor();
minimum("HF_pabs_fixed","AbsolutePressure",fixed,true);if(!flap.isEmpty())minimum("HF_pabs_flap","AbsolutePressure",flap,true);minimum("HF_pabs_liquid_all","AbsolutePressure",regions,true);
UserFieldFunction near=field("HYDRO_NearFoilMask","($$Position[0] > <-0.15 m> && $$Position[0] < <1.5 m> && $$Position[2] > <-0.3 m> && $$Position[2] < <0.35 m>) ? 1 : 0",new Dimensions());
ThresholdPart np=s.getPartManager().createThresholdPart();np.setPresentationName("HYDRO nearby liquid");np.getInputParts().setObjects(regions);np.setFieldFunction(near);np.setRange(new DoubleVector(new double[]{.5,1.5}));np.setMode(ThresholdMode.BETWEEN_TAG);minimum("HF_pabs_near","AbsolutePressure",List.of(np),true);
if(!flap.isEmpty()){Dimensions ld=new Dimensions();ld.setLength(1);UserFieldFunction radial=field("HYDRO_HingeRadius","sqrt(pow($$Position[0] - <"+xh+" m>,2) + pow($$Position[2] - <"+zh+" m>,2))",ld);ThresholdPart gap=s.getPartManager().createThresholdPart();gap.setPresentationName("HYDRO hinge gap radial band");gap.getInputParts().setObjects(regions);gap.setFieldFunction(radial);gap.setRange(new DoubleVector(new double[]{.03510113219921941,.03760113219921941}));gap.setMode(ThresholdMode.BETWEEN_TAG);minimum("HF_pabs_gap","AbsolutePressure",List.of(gap),true);}
minimum("HF_min_volume","Volume",regions,false);minimum("HF_min_quality","CellQuality",regions,false);minimum("HF_min_face_validity","FaceValidity",regions,false);
AreaAverageReport yp=s.getReportManager().createReport(AreaAverageReport.class);yp.setPresentationName("HF_yplus_mean");yp.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));yp.getParts().setObjects(all);yp.createMonitor();
MaxReport ymax=s.getReportManager().createReport(MaxReport.class);ymax.setPresentationName("HF_yplus_max");ymax.setFieldFunction(s.getFieldFunctionManager().getFunction("WallYplus"));ymax.getParts().setObjects(all);ymax.createMonitor();
Files.writeString(out.resolve("normalization.json"),"{\"rho\":1000,\"U\":18,\"mu\":0.001,\"Re\":21420000,\"reference_area_m2\":0.0238,\"qS_N\":3855.6,\"buoyancy_N\":"+buoyancy+",\"temperature_C\":20,\"pvapor_Pa\":2339.214766776897,\"required_margin_Pa\":10000,\"pabs_threshold_Pa\":12339.214766776897,\"turbulence_intensity\":0.001,\"turbulent_viscosity_ratio\":10,\"moment_surface\":\""+(flap.isEmpty()?"intact foil":"flap only")+"\",\"moment_axis\":\"+y\",\"positive_flap\":\"trailing edge toward -z\"}");
}
void scene()throws Exception{
Scene sc=s.getSceneManager().createScene("HYDRO foil and mesh");sc.initializeAndWait();int k=0;for(Region r:regions){PlaneSection p=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));p.setPresentationName("HYDRO midspan "+r.getPresentationName());PartDisplayer d=sc.getDisplayerManager().createPartDisplayer(r.getPresentationName(),-1,1);d.getInputParts().setObjects(p);d.setMesh(true);d.setSurface(false);d.setOutline(false);d.setDisplayerColor(new DoubleVector(k++==0?new double[]{.25,.35,.45}:new double[]{.95,.3,.1}));}
PartDisplayer w=sc.getDisplayerManager().createPartDisplayer("Foil", -1,1);List<Boundary> all=new ArrayList<>(fixed);all.addAll(flap);w.getInputParts().setObjects(all);w.setSurface(true);w.setOutline(true);w.setDisplayerColor(new DoubleVector(new double[]{.1,.4,.75}));
sc.getCurrentView().setInput(new DoubleVector(new double[]{.60,.02,.025}),new DoubleVector(new double[]{.60,-3,.025}),new DoubleVector(new double[]{0,0,1}),.68,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);sc.printAndWait(out.resolve("mesh_foil.png").toString(),1,1300,700);
sc.getCurrentView().setInput(new DoubleVector(new double[]{xh,.02,zh}),new DoubleVector(new double[]{xh,-3,zh}),new DoubleVector(new double[]{0,0,1}),.065,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);sc.printAndWait(out.resolve("mesh_hinge.png").toString(),1,1100,800);
}

double rv(String n){return s.getReportManager().getReport(n).getReportMonitorValue();}
double mean(List<double[]> a,int lo,int hi,int j){double v=0;for(int k=lo;k<hi;k++)v+=a.get(k)[j];return v/(hi-lo);}
void captureFields(String label)throws Exception{StringBuilder b=new StringBuilder("time="+s.getSolution().getPhysicalTime()+" initialized="+s.getSolution().isInitialized()+"\n");for(String n:List.of("Density","Pressure","AbsolutePressure","Velocity","TurbulentKineticEnergy","SpecificDissipationRate")){if(!s.getFieldFunctionManager().hasFunction(n))continue;FieldFunction f=s.getFieldFunctionManager().getFunction(n);if(n.equals("Velocity"))f=f.getMagnitudeFunction();MinReport mi=s.getReportManager().createReport(MinReport.class);MaxReport ma=s.getReportManager().createReport(MaxReport.class);mi.getParts().setObjects(regions);ma.getParts().setObjects(regions);mi.setFieldFunction(f);ma.setFieldFunction(f);b.append(n+" min="+mi.getReportMonitorValue()+" max="+ma.getReportMonitorValue()+"\n");s.getReportManager().removeObjects(mi,ma);}Files.writeString(out.resolve("fields_"+label+".txt"),b.toString());}

double[] flapBounds(){double[] values=new double[6];for(int j=0;j<3;j++){FieldFunction pos=s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j);MinReport lo=s.getReportManager().createReport(MinReport.class);MaxReport hi=s.getReportManager().createReport(MaxReport.class);lo.getParts().setObjects(flap);hi.getParts().setObjects(flap);lo.setFieldFunction(pos);hi.setFieldFunction(pos);values[2*j]=lo.getReportMonitorValue();values[2*j+1]=hi.getReportMonitorValue();s.getReportManager().removeObjects(lo,hi);}return values;}
void checkPose(String stage)throws Exception{if(savedFlapBounds==null)return;double[] current=flapBounds();Files.writeString(out.resolve("pose_bounds_"+stage+".txt"),Arrays.toString(current));for(int k=0;k<6;k++)if(Math.abs(current[k]-savedFlapBounds[k])>1e-8)throw new IllegalStateException("Static mesh pose changed at "+stage+": "+Arrays.toString(current));}
void suspendMotionForSteady()throws Exception{
if(!variant.equals("SP_C"))return;StationaryMotion stationary=null;for(Motion motion:s.get(MotionManager.class).getObjects())if(motion instanceof StationaryMotion)stationary=(StationaryMotion)motion;if(stationary==null)throw new IllegalStateException("Native stationary motion absent");
savedFlapBounds=flapBounds();Files.writeString(out.resolve("pose_bounds_before_suspend.txt"),Arrays.toString(savedFlapBounds));
for(Region r:regions){MotionSpecification spec=r.getValues().get(MotionSpecification.class);Motion motion=spec.getMotion();if(motion instanceof RotatingMotion){String law=((RotationAngle)((RotatingMotion)motion).getRotationSpecification()).getRotationAngle().getDefinition();if(!law.matches("<[+-]?[0-9.]+ deg>"))throw new IllegalStateException("Steady initializer requires constant prescribed angle");savedMotions.put(r,motion);spec.setMotion(stationary);}}
if(savedMotions.isEmpty()&&steadyResume){
RotatingMotion found=null;for(Motion m:s.get(MotionManager.class).getObjects())if(m instanceof RotatingMotion){if(found!=null)throw new IllegalStateException("Ambiguous stored rotation");found=(RotatingMotion)m;}
if(found==null)throw new IllegalStateException("Stored rotation missing from steady checkpoint");
String law=((RotationAngle)found.getRotationSpecification()).getRotationAngle().getDefinition();if(!law.matches("<[+-]?[0-9.]+ deg>"))throw new IllegalStateException("Constant pose required");
savedMotions.put(s.getRegionManager().getRegion("FlapOverset"),found);
}
if(savedMotions.isEmpty())throw new IllegalStateException("SP_C prescribed motion not found");note("Temporarily stationary at existing pose for steady initialization; source unchanged");checkPose("after_suspend");
}
void restoreMotionForUnsteady()throws Exception{
if(savedMotions.isEmpty())return;for(Map.Entry<Region,Motion> entry:savedMotions.entrySet())entry.getKey().getValues().get(MotionSpecification.class).setMotion(entry.getValue());
List<Solver> frozen=new ArrayList<>();try{for(Solver solver:s.getSolverManager().getObjects())if(solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb"))if(!solver.getFrozen()){solver.setFrozen(true);frozen.add(solver);}for(SolverStoppingCriterion criterion:s.getSolverStoppingCriterionManager().getObjects())if(criterion instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)criterion).setMaximumNumberInnerIterations(1);s.getSimulationIterator().step(1);checkPose("after_restore_and_frozen_step");}
finally{for(Solver solver:frozen)solver.setFrozen(false);for(SolverStoppingCriterion criterion:s.getSolverStoppingCriterionManager().getObjects())if(criterion instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)criterion).setMaximumNumberInnerIterations(15);}
Files.writeString(out.resolve("motion_restored.json"),"{\"motion_suspended_for_steady\":true,\"motion_restored\":true,\"mesh_pose_preserved_tolerance_m\":1e-8,\"frozen_motion_settle_steps\":1,\"training_approved\":false}");
}
FieldFunction namedField(String display,String fallback){if(s.getFieldFunctionManager().hasFunction(fallback))return s.getFieldFunctionManager().getFunction(fallback);for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(display))return f;throw new IllegalStateException("Required field absent: "+display);}
ElementCountReport count(String name,FieldFunction ff,double lo,double hi,Representation rep){ThresholdPart p=s.getPartManager().createThresholdPart();p.setPresentationName(name);p.getInputParts().setObjects(regions);p.setFieldFunction(ff);p.setRange(new DoubleVector(new double[]{lo,hi}));p.setMode(ThresholdMode.BETWEEN_TAG);ElementCountReport r=s.getReportManager().createReport(ElementCountReport.class);r.setPresentationName(name);r.getParts().setObjects(p);r.setRepresentation(rep);return r;}
void auditFull(String label,long expected)throws Exception{
Representation full=s.getRepresentationManager().getObject("Overset Mesh");long total=0,active=0,inactive=0,acceptor=0,errors=0,fallback=0;double minV=Double.POSITIVE_INFINITY,minQ=Double.POSITIVE_INFINITY,maxRatio=0;Map<Integer,Long> methods=new TreeMap<>();
for(Region r:regions){PlaneSection plane=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));
XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(plane);t.setRepresentation(full);t.setExtractVertexData(false);t.setFieldFunctions(List.of(namedField("Overset Cell Status","OversetCellStatus"),namedField("Overset Error Status","OversetErrorStatus"),namedField("Overset Interpolation Type","OversetInterpolationType"),namedField("Overset Interpolation Cell Size Ratio","Overset Interpolation Cell Size Ratio"),s.getFieldFunctionManager().getFunction("Volume"),s.getFieldFunctionManager().getFunction("CellQuality")));t.extract();Path file=out.resolve(r.getPresentationName()+"_"+label+"_full_plane.csv");t.export(file.toString());
try(BufferedReader reader=Files.newBufferedReader(file)){String line=reader.readLine();if(line==null||!line.startsWith("\"Overset Cell Status\""))throw new IllegalStateException("Unexpected full-plane export schema");while((line=reader.readLine())!=null){if(line.isBlank())continue;String[] a=line.split(",");double status=Double.parseDouble(a[0]),error=Double.parseDouble(a[1]),method=Double.parseDouble(a[2]),ratio=Double.parseDouble(a[3]),v=Double.parseDouble(a[4]),q=Double.parseDouble(a[5]);if(!Double.isFinite(status+error+method+ratio+v+q)||Math.abs(status)>2.001||error<0||error>100||method < -2||method>7||v<=0||v>1||q<=0||q>1.001)throw new IllegalStateException("Invalid full-plane diagnostic values");total++;minV=Math.min(minV,v);minQ=Math.min(minQ,q);if(status==0)active++;else if(status==1)inactive++;else if(status==-2||status==-1){acceptor++;if(ratio<=0)throw new IllegalStateException("Invalid acceptor size ratio");maxRatio=Math.max(maxRatio,ratio);methods.merge((int)method,1L,Long::sum);}else throw new IllegalStateException("Invalid cell status");if(error>0)errors++;if(method>=4&&method<=6)fallback++;}}
s.getTableManager().removeObjects(t);s.getPartManager().removeObjects(plane);
}
String msg="time="+s.getSolution().getPhysicalTime()+" total="+total+" active="+active+" inactive="+inactive+" acceptors="+acceptor+" errors="+errors+" difficult_interpolation="+fallback+" min_volume="+minV+" min_quality="+minQ+" max_acceptor_size_ratio="+maxRatio+" methods="+methods+"\n";
Files.writeString(out.resolve("full_audit_"+label+".txt"),msg);s.println("FULL_OVERSET_AUDIT "+msg);
if(label.equals("after_first_step")&&methods.getOrDefault(2,0L)>0)throw new IllegalStateException("Distance-weighted option not reflected in native full-plane audit");
if(total!=expected||active<1||acceptor<1||errors!=0||fallback!=0)throw new IllegalStateException("Complete Overset connectivity check failed");
}




void captureComparison(String label)throws Exception{
Representation rep=s.getRepresentationManager().getObject("Volume Mesh");
List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("Pressure","AbsolutePressure","Volume","CellQuality","WallDistance","TurbulentKineticEnergy","SpecificDissipationRate","TurbulentViscosityRatio","OversetCellStatus","OversetCellType","OversetErrorStatus","OversetInterpolationType","Overset Interpolation Cell Size Ratio"))if(s.getFieldFunctionManager().hasFunction(name))fields.add(s.getFieldFunctionManager().getFunction(name));
for(int axis=0;axis<3;axis++)fields.add(s.getFieldFunctionManager().getFunction("Velocity").getComponentFunction(axis));
for(Region r:regions){XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(r);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(fields);tab.extract();tab.export(out.resolve(r.getPresentationName()+"_"+label+"_volume.csv").toString());s.getTableManager().removeObjects(tab);}
StringBuilder force=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");int j=0;
for(List<Boundary> walls:List.of(fixed,flap)){String group=j++==0?"main":"flap";ForceReport f=s.getReportManager().createReport(ForceReport.class);f.setPressureOption(FluidLoadsReportPressureOption.SP_UC);f.getDirection().setComponents(0,0,1);f.getParts().setObjects(walls);f.getReportMonitorValue();force.append(group+"_pressure_force="+f.getPressureValue()+"\n"+group+"_shear_force="+f.getShearValue()+"\n"+group+"_total_force="+f.getValue()+"\n");s.getReportManager().removeObjects(f);
XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);tab.getParts().setObjects(walls);tab.setRepresentation(rep);tab.setExtractVertexData(false);tab.setFieldFunctions(List.of(s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("AbsolutePressure"),s.getFieldFunctionManager().getFunction("WallYplus")));tab.extract();tab.export(out.resolve(group+"_"+label+"_wall.csv").toString());s.getTableManager().removeObjects(tab);}
Files.writeString(out.resolve("forces_"+label+".txt"),force.toString());
StringBuilder res=new StringBuilder("time="+s.getSolution().getPhysicalTime()+"\n");
for(Monitor mon:s.getMonitorManager().getObjects())if(mon instanceof ResidualMonitor){ResidualMonitor rm=(ResidualMonitor)mon;try{res.append(rm.getPresentationName()+" enabled="+rm.getEnabled()+" normalized="+rm.isNormalized()+" normalization="+rm.getNormalizationType().getClass().getSimpleName()+" factor="+rm.getNormalizationType().getNormalizationFactor()+"\n");}catch(Exception metadataError){res.append("OPTIONAL_METADATA_ERROR "+rm.getPresentationName()+" "+metadataError+"\n");}try{rm.export(out.resolve("residual_"+label+"_"+rm.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}catch(Exception exportError){res.append("RESIDUAL_EXPORT_INCOMPLETE "+rm.getPresentationName()+" "+exportError+"\n");}}
Files.writeString(out.resolve("residual_normalization_"+label+".txt"),res.toString());
}



final boolean SMOKE=false;
final String LAW="<0 deg>";

double ramp(double t){return 0.0;}
double rampRate(double t){return 0.0;}
double speedDown(double t){
 double x=Math.max(0.0,Math.min(1.0,(t-.65)/.4));
 return 18.0-8.0*(10*x*x*x-15*Math.pow(x,4)+6*Math.pow(x,5));
}
void setInletU(double u)throws Exception{
 if(!Double.isFinite(u)||u<10.0||u>18.0)throw new IllegalStateException("Speed ramp out of bounds");
 int n=0;
 for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary){
  if(b.getConditions().get(InletVelocityOption.class).getSelected()!=InletVelocityOption.Type.COMPONENTS.getValue())throw new IllegalStateException("Inlet velocity specification changed");
  VectorProfile p=b.getValues().get(VelocityProfile.class);
  p.setMethod(ConstantVectorProfileMethod.class);
  p.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponents(u,0,0);
  n++;
 }
 if(n==0)throw new IllegalStateException("No inlet found");
 double qs=11.9*u*u;
 ((ExpressionReport)s.getReportManager().getReport("HF_CL_hydro")).setDefinition("($"+"{HF_Fz_NReport} - <22.666963538808645 N>)/<"+qs+" N>");
 ((ExpressionReport)s.getReportManager().getReport("HF_CD")).setDefinition("$"+"{HF_Fx_NReport}/<"+qs+" N>");
}
boolean residualGate()throws Exception{boolean ok=true;for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor&&!m.getPresentationName().equals("Y-momentum")){Path p=out.resolve("residual_latest_"+m.getPresentationName()+".csv");((ResidualMonitor)m).export(p.toString());List<Double> v=new ArrayList<>();for(String line:Files.readAllLines(p)){String[] a=line.replace("\"","").split(",");try{if(a.length>=2)v.add(Double.parseDouble(a[1]));}catch(NumberFormatException ignored){}}if(v.size()<40)throw new IllegalStateException("Missing residual history");double first=v.get(v.size()-40),last=v.get(v.size()-1);ok&=Double.isFinite(first+last)&&last<=.01*Math.max(Math.abs(first),1e-30);}return ok;}

<T extends Report> T reuseReport(Class<T> cls){for(Report r:s.getReportManager().getObjects())if(cls.isInstance(r))return cls.cast(r);return s.getReportManager().createReport(cls);}
public void execute(){s=getActiveSimulation();variant="SP_C";Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();out=Paths.get("F:/ntnu/flap_control/independent_cfd_diagnostics/C0_speed_down_20261103/run_"+System.getenv("NTNU_HYDRO_RUN_ID"));int done=0;boolean stable=false;List<double[]> windows=new ArrayList<>();int goodWindows=0;double t0=s.getSolution().getPhysicalTime();
try{
Files.createDirectories(out);guard();

// Independent diagnostic: only verified C0 solution at 0deg/18mps.
Path source=root.resolve("cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim").toAbsolutePath().normalize();
if(!"YES".equals(System.getenv("NTNU_C0_SPEEDDOWN_ALLOWED")))throw new IllegalStateException("Requires explicit independent diagnostic authorization");
if(!input.equals(source)||Math.abs(t0-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560)throw new IllegalStateException("Only native reopened C0 t=0.650s/iter=11560 allowed");
for(Region r:s.getRegionManager().getRegions()){regions.add(r);for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(r.getPresentationName().equals("FlapOverset"))flap.add(b);else fixed.add(b);}}
if(regions.size()!=2||fixed.isEmpty()||flap.isEmpty())throw new IllegalStateException("Unexpected regions");
PhysicsContinuum pc=regions.get(0).getPhysicsContinuum();
if(((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()!=333939)throw new IllegalStateException("Mesh changed");
if(pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().getSelected()!=FlowUpwindOption.Type.SECOND_ORDER.getValue()||pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().getSelected()!=UpwindOption.Type.SECOND_ORDER.getValue())throw new IllegalStateException("Second order required");
if(pc.getModelManager().getModel(OversetConservationModel.class).getOversetConservationOption().getSelected()!=OversetConservationOption.Type.FLUX_CORRECTION.getValue())throw new IllegalStateException("Flux correction required");
for(Solver solver:s.getSolverManager().getObjects())if((solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb"))&&solver.getFrozen())throw new IllegalStateException("Hydrodynamic solvers frozen");
ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-.002)>1e-12||us.getTimeDiscretizationOption().getSelected()!=TimeDiscretizationOption.Type.SECOND_ORDER.getValue())throw new IllegalStateException("Time settings changed");
SegregatedFlowSolver fs=s.getSolverManager().getSolver(SegregatedFlowSolver.class);if(Math.abs(fs.getVelocitySolver().getUrf()-.8)>1e-12||Math.abs(fs.getPressureSolver().getUrf()-.2)>1e-12)throw new IllegalStateException("URF changed");
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){if(c instanceof InnerIterationStoppingCriterion){if(!c.getIsUsed()||((InnerIterationStoppingCriterion)c).getMaximumNumberInnerIterations()!=40)throw new IllegalStateException("40inner required");}else c.setIsUsed(false);}
for(Boundary b:s.getRegionManager().getRegion("Background").getBoundaryManager().getBoundaries())if(b.getPresentationName().endsWith(".top")&&b.getConditions().get(BackflowSpecification.class).getBackflowVelocityDirectionOption().getSelected()!=BackflowVelocityDirectionOption.Type.EXTRAPOLATED.getValue())throw new IllegalStateException("Extrapolated top required");

RotatingMotion rot=(RotatingMotion)s.getRegionManager().getRegion("FlapOverset").getValues().get(MotionSpecification.class).getMotion();
if(SMOKE&&!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<0 deg>"))throw new IllegalStateException("C0 zero angle required");
if(!SMOKE&&!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals(LAW))throw new IllegalStateException("Ramp law changed");
((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition(LAW);
Vector3 point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double angle=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh));if(Math.abs(angle-ramp(t0))>1e-5)throw new IllegalStateException("Starting pose mismatch");
AreaAverageReport[] center=new AreaAverageReport[3];double[] startCenter=new double[3];for(int j=0;j<3;j++){center[j]=s.getReportManager().createReport(AreaAverageReport.class);center[j].getParts().setObjects(flap);center[j].setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));startCenter[j]=center[j].getReportMonitorValue();}
List<Boundary> outer=new ArrayList<>();for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary||b.getBoundaryType() instanceof PressureBoundary)outer.add(b);
MassFlowReport mass=s.getReportManager().createReport(MassFlowReport.class);mass.getParts().setObjects(outer);
UserFieldFunction of=field("PLUS2_omega_floor","($OversetCellStatus == 0 && $SpecificDissipationRate <= <1.0001e-10 /s>) ? 1 : 0",new Dimensions()),kf=field("PLUS2_k_floor","($OversetCellStatus == 0 && $TurbulentKineticEnergy <= <1.0001e-10 J/kg>) ? 1 : 0",new Dimensions());
ElementCountReport oc=count("PLUS2 omega floor",of,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh")),kc=count("PLUS2 k floor",kf,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh")),ec=count("PLUS2 overset errors",namedField("Overset Error Status","OversetErrorStatus"),.5,100,s.getRepresentationManager().getObject("Volume Mesh"));
MaxReport visc=s.getReportManager().createReport(MaxReport.class);visc.getParts().setObjects(regions);visc.setFieldFunction(s.getFieldFunctionManager().getFunction("TurbulentViscosityRatio"));
MaxReport speed=s.getReportManager().createReport(MaxReport.class);speed.getParts().setObjects(regions);speed.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());
AverageWorkerCommunicationTimeReport comm=reuseReport(AverageWorkerCommunicationTimeReport.class);
TimeStepCpuTimeReport cpu=reuseReport(TimeStepCpuTimeReport.class);TimeStepElapsedTimeReport elapsed=reuseReport(TimeStepElapsedTimeReport.class);
captureFields("readback");captureComparison("readback");auditFull("readback",333939);scene();
Files.writeString(out.resolve("preflight.json"),"{\"time\":"+t0+",\"iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"actual_angle_deg\":"+angle+",\"flow_frozen\":false,\"dt\":0.002,\"inner\":40,\"mesh\":333939,\"initial_CL\":"+rv("HF_CL_hydro")+",\"initial_CD\":"+rv("HF_CD")+",\"initial_Mh\":"+rv("HF_Mh_Nm")+"}");
try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"));BufferedWriter pw=Files.newBufferedWriter(out.resolve("pressure_zones.csv"))){
w.write("step,time_s,Fx_N,Fz_N,CL_hydro,CD,Mh_Nm,p_absolute_min_Pa,cavitation_margin_Pa,mass_imbalance_relative,omega_floor_cells,k_floor_cells,max_turbulent_viscosity_ratio,overset_error_cells,min_volume_m3,min_cell_quality,min_face_validity,max_speed_m_s,yplus_max,native_iteration,solver_step_seconds,native_step_elapsed,native_step_cpu,worker_communication_before,worker_communication_after,start_epoch_ms,end_epoch_ms,measured,flap_angle_deg,flap_angular_velocity_deg_s,measured_angle_deg,center_error_m,U_m_s,qS_N\n");pw.write("step,time_s,zone,pabs_Pa,x_m,y_m,z_m\n");
for(int i=1;i<=20;i++){if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Pause requested");
double commandedU=speedDown(s.getSolution().getPhysicalTime()+.002);setInletU(commandedU);double cb=comm.getReportMonitorValue();long epoch=System.currentTimeMillis(),start=System.nanoTime();s.getSimulationIterator().step(1);double seconds=(System.nanoTime()-start)/1e9;long endEpoch=System.currentTimeMillis();done=i;double ca=comm.getReportMonitorValue(),nt=elapsed.getReportMonitorValue(),nc=cpu.getReportMonitorValue(),t=s.getSolution().getPhysicalTime();
if(Math.abs(t-(t0+i*.002))>1e-9)throw new IllegalStateException("Time advance mismatch");
double fx=rv("HF_Fx_N"),fz=rv("HF_Fz_N"),cl=rv("HF_CL_hydro"),cd=rv("HF_CD"),mh=rv("HF_Mh_Nm"),p=Double.POSITIVE_INFINITY;
for(String zone:List.of("fixed","flap","near","gap","liquid_all")){MinReport pr=(MinReport)s.getReportManager().getReport("HF_pabs_"+zone);double pv=pr.getReportMonitorValue();p=Math.min(p,pv);double[] loc=new double[3];for(int j=0;j<3;j++)loc[j]=pr.getCollocatedValue(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));pw.write(i+","+t+","+zone+","+pv+","+loc[0]+","+loc[1]+","+loc[2]+"\n");}pw.flush();
double bal=Math.abs(mass.getReportMonitorValue())/10800.,om=oc.getReportMonitorValue(),k=kc.getReportMonitorValue(),v=visc.getReportMonitorValue(),err=ec.getReportMonitorValue(),vol=rv("HF_min_volume"),q=rv("HF_min_quality"),valid=rv("HF_min_face_validity"),u=speed.getReportMonitorValue();
point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double actual=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh)),cmd=ramp(t),rate=rampRate(t),a=Math.toRadians(cmd-ramp(t0));double dx=startCenter[0]-xh,dz=startCenter[2]-zh,ce=0;double[] expected={xh+dx*Math.cos(a)+dz*Math.sin(a),startCenter[1],zh-dx*Math.sin(a)+dz*Math.cos(a)};for(int j=0;j<3;j++)ce=Math.max(ce,Math.abs(center[j].getReportMonitorValue()-expected[j]));
if(Math.abs(actual-cmd)>1e-5||ce>1e-7)throw new IllegalStateException("Rigid body motion mismatch");
w.write(i+","+t+","+fx+","+fz+","+cl+","+cd+","+mh+","+p+","+(p-2339.214766776897)+","+bal+","+om+","+k+","+v+","+err+","+vol+","+q+","+valid+","+u+","+rv("HF_yplus_max")+","+s.getSimulationIterator().getCurrentIteration()+","+seconds+","+nt+","+nc+","+cb+","+ca+","+epoch+","+endEpoch+","+false+","+cmd+","+rate+","+actual+","+ce+","+commandedU+","+(11.9*commandedU*commandedU)+"\n");w.flush();
if(!Double.isFinite(fx+fz+mh+p+bal+om+k+v+err+vol+q+valid+u)||p<=12339.214766776897||bal>=1e-4||om>0||k>0||v>=99999||err>0||vol<=0||q<=0||valid<.5||u>180)throw new IllegalStateException("Strict pressure/mass/turbulence/mesh guard violated");

auditFull("latest",333939);
note("Ramp step="+i+" time="+t+" delta_deg="+cmd+" angular_rate="+rate+" pabs="+p);
if(t>=.85-1e-9)windows.add(new double[]{cl,cd,mh,p,bal});
int globalStep=(int)Math.round((t-.65)/.002);
if(globalStep%25==0){boolean residualOk=residualGate();Files.writeString(out.resolve("convergence_latest.json"),"{\"time\":"+t+",\"post_ramp_samples\":"+windows.size()+",\"residual_gate\":"+residualOk+"}");
 if(windows.size()>=50){boolean forceOk=true;int n=windows.size();for(int col=0;col<3;col++){double aa=mean(windows,n-25,n,col),bb=mean(windows,n-50,n-25,col),lo=Double.POSITIVE_INFINITY,hi=-lo;for(int wi=n-25;wi<n;wi++){lo=Math.min(lo,windows.get(wi)[col]);hi=Math.max(hi,windows.get(wi)[col]);}forceOk&=Math.abs(aa-bb)<.005*Math.max(1e-6,Math.abs(aa))&&(hi-lo)<.01*Math.max(1e-6,Math.abs(aa));}goodWindows=forceOk&&residualOk?goodWindows+1:0;if(goodWindows>=2&&windows.size()>=75){stable=true;break;}}
}
if(globalStep%50==0){captureComparison("checkpoint_"+globalStep);s.saveState(out.resolve("checkpoint_step_"+i+".sim").toString());}

}}

captureFields("final");captureComparison("final");auditFull("final",333939);scene();s.saveState(out.resolve("checkpoint.sim").toString());
String status="speed_down_smoke_passed_not_scientific_validation";
Files.writeString(out.resolve("status.json"),"{\"status\":\""+status+"\",\"steps\":"+done+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"iteration\":"+s.getSimulationIterator().getCurrentIteration()+",\"force_windows_stable\":"+stable+",\"scientific_approved\":false,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());try{captureFields("failure");captureComparison("failure");auditFull("failure",333939);}catch(Exception diagnostic){Files.writeString(out.resolve("failure_export_error.txt"),diagnostic.toString());}boolean paused=e.getMessage()!=null&&e.getMessage().equals("Pause requested");s.saveState(out.resolve(paused?"paused_checkpoint.sim":"error_checkpoint.sim").toString());Files.writeString(out.resolve("status.json"),"{\"status\":\""+(paused?"ramp_paused":"ramp_failed")+"\",\"steps\":"+done+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"scientific_approved\":false}");if(paused)return;}catch(Exception ex){s.println(ex);}throw new RuntimeException(e);}
}
}
