package macro;
import star.common.*;import star.overset.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.meshing.*;import star.material.*;import star.flow.*;import star.segregatedflow.*;import star.turbulence.*;import star.kwturb.*;import star.motion.*;import star.vis.*;import star.sweptmesher.*;import star.prismmesher.*;import java.nio.file.*;import java.io.*;import java.util.*;

public class RelocationNativeAudit extends StarMacro {
Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;
List<Region> regions=new ArrayList<>();List<Boundary> fixed=new ArrayList<>(),flap=new ArrayList<>();
String val(Object o,String method){try{return String.valueOf(o.getClass().getMethod(method).invoke(o));}catch(Exception e){return "";}}
void inspect(Object o,StringBuilder b){
 b.append(o.getClass().getName());
 if(o instanceof EnumeratedOption)b.append(" selected="+((EnumeratedOption)o).getSelected());
 if(o instanceof BackflowSpecification){BackflowSpecification v=(BackflowSpecification)o;b.append(" direction="+v.getBackflowVelocityDirectionOption().getSelected()+" pressure="+v.getReversedFlowPressureOption().getSelected()+" scalar="+v.getReversedFlowScalarOption().getSelected());}
 if(o instanceof ScalarProfile){ScalarProfile p=(ScalarProfile)o;b.append(" method="+p.getMethod().getClass().getName());
  if(p.getMethod() instanceof ConstantScalarProfileMethod)b.append(" value="+p.getMethod(ConstantScalarProfileMethod.class).getQuantity().getValue());
  if(p.getMethod() instanceof FunctionScalarProfileMethod){FieldFunction f=p.getMethod(FunctionScalarProfileMethod.class).getFieldFunction();b.append(" function="+f.getFunctionName());if(f instanceof UserFieldFunction)b.append(" definition="+((UserFieldFunction)f).getDefinition());}}
 if(o instanceof VectorProfile){VectorProfile p=(VectorProfile)o;b.append(" method="+p.getMethod().getClass().getName());if(p.getMethod() instanceof ConstantVectorProfileMethod)b.append(" value="+p.getMethod(ConstantVectorProfileMethod.class).getQuantity().getVector());}
 b.append("\n");
}
FieldFunction namedField(String display,String fallback){if(s.getFieldFunctionManager().hasFunction(fallback))return s.getFieldFunctionManager().getFunction(fallback);for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(display))return f;throw new IllegalStateException("Required field absent: "+display);}
ElementCountReport count(String name,FieldFunction ff,double lo,double hi,Representation rep){ThresholdPart p=s.getPartManager().createThresholdPart();p.setPresentationName(name);p.getInputParts().setObjects(regions);p.setFieldFunction(ff);p.setRange(new DoubleVector(new double[]{lo,hi}));p.setMode(ThresholdMode.BETWEEN_TAG);ElementCountReport r=s.getReportManager().createReport(ElementCountReport.class);r.setPresentationName(name);r.getParts().setObjects(p);r.setRepresentation(rep);return r;}
void auditFull(String label,long expected)throws Exception{
Representation full=s.getRepresentationManager().getObject("Overset Mesh");long total=0,active=0,inactive=0,acceptor=0,errors=0,fallback=0;double minV=Double.POSITIVE_INFINITY,minQ=Double.POSITIVE_INFINITY,maxRatio=0;Map<Integer,Long> methods=new TreeMap<>();
for(Region r:regions){PlaneSection plane=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));
XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(plane);t.setRepresentation(full);t.setExtractVertexData(false);t.setFieldFunctions(List.of(namedField("Overset Cell Status","OversetCellStatus"),namedField("Overset Error Status","OversetErrorStatus"),namedField("Overset Interpolation Type","OversetInterpolationType"),namedField("Overset Interpolation Cell Size Ratio","Overset Interpolation Cell Size Ratio"),s.getFieldFunctionManager().getFunction("Volume"),s.getFieldFunctionManager().getFunction("CellQuality")));t.extract();Path file=out.resolve(r.getPresentationName()+"_"+label+"_full_plane.csv");t.export(file.toString());
try(BufferedReader reader=Files.newBufferedReader(file)){String line=reader.readLine();if(line==null||!line.startsWith("\"Overset Cell Status\""))throw new IllegalStateException("Unexpected full-plane export schema");while((line=reader.readLine())!=null){if(line.isBlank())continue;String[] a=line.split(",");double status=Double.parseDouble(a[0]),error=Double.parseDouble(a[1]),method=Double.parseDouble(a[2]),ratio=Double.parseDouble(a[3]),v=Double.parseDouble(a[4]),q=Double.parseDouble(a[5]);if(!Double.isFinite(status+error+method+ratio+v+q)||Math.abs(status)>2.001||error<0||error>100||method < -2||method>7||v<=0||v>1||q<=0||q>1.001)throw new IllegalStateException("Invalid full-plane diagnostic values");total++;minV=Math.min(minV,v);minQ=Math.min(minQ,q);if(status==0)active++;else if(status==1)inactive++;else if(status==-2||status==-1){acceptor++;if(ratio<=0)throw new IllegalStateException("Invalid acceptor size ratio");maxRatio=Math.max(maxRatio,ratio);methods.merge((int)method,1L,Long::sum);}else throw new IllegalStateException("Invalid cell status");if(error>0)errors++;if(method>=4&&method<=6)fallback++;}}
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



public void execute(){s=getActiveSimulation();Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();
boolean c=input.toString().contains("SP_C_split0_overset");String variant=c?"C0":"B0";
out=root.resolve("audit/relocation_native_20261103_"+variant);
try{
 if(!input.startsWith(root.resolve("cases"))||!input.getParent().getFileName().toString().startsWith("relocation_reopen_"))throw new IllegalStateException("Only recovery working copy allowed");
 if(Files.exists(out.resolve("status.json")))throw new IllegalStateException("Audit already exists; do not overwrite");
 Files.createDirectories(out);double t=s.getSolution().getPhysicalTime();int it=s.getSimulationIterator().getCurrentIteration();
 Files.writeString(out.resolve("initial_native_counters.txt"),"source="+input+"\ninitialized="+s.getSolution().isInitialized()+"\ntime="+t+"\niteration="+it+"\ngpus="+s.getNumberOfGpgpus()+"\n");
 if(Math.abs(t-(c?.65:.5))>1e-9||it!=(c?11560:6250)||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Checkpoint counter mismatch");
 s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
 for(Region r:s.getRegionManager().getRegions())if(r.getPhysicsContinuum()!=null&&r.getPhysicsContinuum().getPresentationName().equals("HYDRO water SST singlephase")){regions.add(r);for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(b.getPresentationName().toLowerCase(Locale.ROOT).contains("flap"))flap.add(b);else fixed.add(b);}}
 if(regions.size()!=(c?2:1)||fixed.isEmpty()||flap.isEmpty())throw new IllegalStateException("Unexpected physical parts");
 StringBuilder b=new StringBuilder("input="+input+"\nphysical_time_s="+t+"\niteration="+it+"\nisInitialized_flag="+s.getSolution().isInitialized()+"\n");
 PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");
 for(Model m:pc.getModelManager().getObjects())b.append("model="+m.getClass().getName()+"\n");
 for(Object v:pc.getReferenceValues().getObjects())b.append("reference="+v.getClass().getName()+" "+val(v,"getSIValue")+" "+val(v,"getVector")+"\n");
 Material water=pc.getModelManager().getModel(SingleComponentLiquidModel.class).getMaterial();
 b.append("density="+((ConstantMaterialPropertyMethod)water.getMaterialProperties().getMaterialProperty(ConstantDensityProperty.class).getMethod()).getQuantity().getValue()+"\n");
 b.append("viscosity="+((ConstantMaterialPropertyMethod)water.getMaterialProperties().getMaterialProperty(DynamicViscosityProperty.class).getMethod()).getQuantity().getValue()+"\n");
 SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
 b.append("velocity_urf="+flow.getVelocitySolver().getUrf()+"\npressure_urf="+flow.getPressureSolver().getUrf()+"\ndynamic_urf="+flow.getVelocitySolver().getUseDynamicLocalUrf()+"\ncontinuity_initialization="+flow.getContinuityInitialization()+"\n");
 b.append("flow_convection="+pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().getSelected()+"\nSST_convection="+pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().getSelected()+"\ndt="+us.getTimeStep().getValue()+"\ntime_order="+us.getTimeDiscretizationOption().getSelected()+"\n");
 for(SolverStoppingCriterion sc:s.getSolverStoppingCriterionManager().getObjects())if(sc instanceof InnerIterationStoppingCriterion)b.append("inner="+((InnerIterationStoppingCriterion)sc).getMaximumNumberInnerIterations()+" used="+sc.getIsUsed()+"\n");
 for(Solver solver:s.getSolverManager().getObjects())b.append("solver="+solver.getClass().getName()+" frozen="+solver.getFrozen()+"\n");
 for(Region r:regions){b.append("REGION="+r.getPresentationName()+"\n");for(Boundary boundary:r.getBoundaryManager().getBoundaries()){b.append("BOUNDARY="+boundary.getPresentationName()+" type="+boundary.getBoundaryType().getClass().getName()+"\n");for(Object x:boundary.getConditions().getObjects())inspect(x,b);for(Object x:boundary.getValues().getObjects())inspect(x,b);}}
 for(Motion motion:s.get(MotionManager.class).getObjects()){b.append("motion="+motion.getPresentationName()+" type="+motion.getClass().getName()+"\n");if(motion instanceof RotatingMotion){RotatingMotion rot=(RotatingMotion)motion;b.append("angle="+((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition()+"\norigin="+val(rot,"getOrigin")+"\naxis="+val(rot,"getAxisDirection")+"\n");}}
 for(String n:List.of("HF_Fx_N","HF_Fz_N","HF_CL_hydro","HF_CD","HF_Mh_Nm","HF_pabs_liquid_all","HF_min_volume","HF_min_quality","HF_min_face_validity","HF_yplus_mean","HF_yplus_max"))b.append(n+"="+s.getReportManager().getReport(n).getReportMonitorValue()+"\n");
 b.append("cells="+((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount()+"\n");
 Files.writeString(out.resolve("native_state.txt"),b.toString());captureComparison("reopened");if(c)auditFull("reopened",333939);
 if(s.getSolution().getPhysicalTime()!=t||s.getSimulationIterator().getCurrentIteration()!=it)throw new IllegalStateException("Audit advanced solution");
 Files.writeString(out.resolve("status.json"),"{\"status\":\"native_readback_complete\",\"time_s\":"+t+",\"iteration\":"+it+",\"solver_steps\":0,\"mesh_regenerated\":false,\"sim_saved\":false}");s.println("RELOCATION_NATIVE_READBACK_COMPLETE "+variant);
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}
}
