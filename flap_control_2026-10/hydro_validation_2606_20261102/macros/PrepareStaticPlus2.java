package macro;
import star.common.*;import star.overset.*;import star.metrics.*;import star.base.neo.*;import star.base.report.*;import star.meshing.*;import star.material.*;import star.flow.*;import star.segregatedflow.*;import star.turbulence.*;import star.kwturb.*;import star.motion.*;import star.vis.*;import star.sweptmesher.*;import star.prismmesher.*;import java.nio.file.*;import java.io.*;import java.util.*;


public class PrepareStaticPlus2 extends StarMacro {
Scene proofScene;Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;List<Region> regions=new ArrayList<>();List<Boundary> fixed=new ArrayList<>(),flap=new ArrayList<>();double xh=.952,zh=.02128173276776986;
void stopGuard()throws Exception{if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Pause requested");}
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



void scene()throws Exception{
Scene sc=s.getSceneManager().createScene("HYDRO foil and mesh");proofScene=sc;sc.initializeAndWait();int k=0;for(Region r:regions){PlaneSection p=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));p.setPresentationName("HYDRO midspan "+r.getPresentationName());PartDisplayer d=sc.getDisplayerManager().createPartDisplayer(r.getPresentationName(),-1,1);d.getInputParts().setObjects(p);d.setMesh(true);d.setSurface(false);d.setOutline(false);d.setDisplayerColor(new DoubleVector(k++==0?new double[]{.25,.35,.45}:new double[]{.95,.3,.1}));}
PartDisplayer w=sc.getDisplayerManager().createPartDisplayer("Foil", -1,1);List<Boundary> all=new ArrayList<>(fixed);all.addAll(flap);w.getInputParts().setObjects(all);w.setSurface(true);w.setOutline(true);w.setDisplayerColor(new DoubleVector(new double[]{.1,.4,.75}));
sc.getCurrentView().setInput(new DoubleVector(new double[]{.60,.02,.025}),new DoubleVector(new double[]{.60,-3,.025}),new DoubleVector(new double[]{0,0,1}),.68,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);sc.printAndWait(out.resolve("mesh_foil.png").toString(),1,1300,700);
sc.getCurrentView().setInput(new DoubleVector(new double[]{xh,.02,zh}),new DoubleVector(new double[]{xh,-3,zh}),new DoubleVector(new double[]{0,0,1}),.065,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);sc.printAndWait(out.resolve("mesh_hinge.png").toString(),1,1100,800);
}



public void execute(){s=getActiveSimulation();Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();out=root.resolve("cases/SP_C_split0_overset/static_plus2_prepared_"+System.getenv("NTNU_HYDRO_RUN_ID"));int completed=0;
try{
if(!input.equals(root.resolve("cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim")))throw new IllegalStateException("Verified hydrodynamic C0 source required; kinematic result must not be used");
if(!Files.readString(root.resolve("audit/KINEMATIC_POC_REVIEW_20261103.json")).contains("\"accepted\": true"))throw new IllegalStateException("Full kinematic sweep not accepted");
if(Math.abs(s.getSolution().getPhysicalTime()-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Source counters or CPU mismatch");
Files.createDirectories(out);stopGuard();s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
Region bg=s.getRegionManager().getRegion("Background"),ov=s.getRegionManager().getRegion("FlapOverset");regions.add(bg);regions.add(ov);
for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(r==ov)flap.add(b);else fixed.add(b);}
RotatingMotion rot=(RotatingMotion)ov.getValues().get(MotionSpecification.class).getMotion();if(!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<0 deg>"))throw new IllegalStateException("Initial angle must be zero");
auditFull("initial",333939);List<Solver> frozen=new ArrayList<>();
for(Solver solver:s.getSolverManager().getObjects())if(solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb")){if(solver.getFrozen())throw new IllegalStateException("Source hydro solver unexpectedly frozen");solver.setFrozen(true);frozen.add(solver);}
((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition("($Time < <0.67 s>) ? <2 deg>*(($Time - <0.65 s>)/<0.02 s>) : <2 deg>");
s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(.002);
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(1);}}
try(BufferedWriter w=Files.newBufferedWriter(out.resolve("pose_preparation.csv"))){w.write("step,time_s,angle_deg,flow_solved\n");for(int k=1;k<=10;k++){stopGuard();s.getSimulationIterator().step(1);completed=k;Vector3 p=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double angle=-Math.toDegrees(Math.atan2(p.z-zh,p.x-xh));if(Math.abs(angle-.2*k)>.001)throw new IllegalStateException("Pose tracking mismatch");auditFull("pose_"+k,333939);w.write(k+","+s.getSolution().getPhysicalTime()+","+angle+",false\n");w.flush();}}
((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition("<2 deg>");
for(Solver solver:frozen)solver.setFrozen(false);
boolean timeCriterion=false;for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(40);}if(c instanceof PhysicalTimeStoppingCriterion){((PhysicalTimeStoppingCriterion)c).getMaximumTime().setValue(.72);c.setIsUsed(true);timeCriterion=true;}}
if(!timeCriterion)throw new IllegalStateException("Expected physical-time stopping criterion absent");
scene();auditFull("prepared",333939);
Files.writeString(out.resolve("PREPARED_NOT_SOLVED.txt"),"Static +2degree case prepared from verified C0t0.650,not from frozen-flow sweep. Ten frozen-flow pose steps advance mesh/time to0.670; old flow fields retained/interpolated as an approximate warm start. No +2degree hydrodynamics solved. Flow/turbulence unfrozen,URANS SST,dt0.002,40inner,URF0.8/0.2,matched BC. Constant+2deg. Maximum time0.720s limits the next diagnostic to25steps. Do not trust initial forces or frozen-step histories. Review temporal restart treatment and require settling/pressure/mass/Overset guards before accepting hydrodynamic results. No automatic Run performed.");
s.saveState(out.resolve("SP_C_plus2_prepared_NOT_SOLVED_2606.sim").toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"static_pose_prepared\",\"angle_deg\":2,\"pose_steps\":"+completed+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"hydrodynamic_steps\":0,\"warm_start_only\":true,\"flow_solvers_frozen\":false,\"maximum_next_time_s\":0.72,\"training_approved\":false}");s.println("STATIC_PLUS2_PREPARED_NOT_SOLVED");
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"static_preparation_failed\",\"pose_steps\":"+completed+"}");s.saveState(out.resolve("preparation_error.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}
}
