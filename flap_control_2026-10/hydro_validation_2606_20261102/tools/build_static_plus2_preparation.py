from pathlib import Path
import subprocess
H=Path(__file__).resolve().parents[1];src=(H/'macros/KinematicPoc333939.java').read_text()
header=src[:src.index('public class')];helpers=src[src.index('FieldFunction namedField('):src.index('public void execute()')]
body=r'''
public class PrepareStaticPlus2 extends StarMacro {
Scene proofScene;Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;List<Region> regions=new ArrayList<>();List<Boundary> fixed=new ArrayList<>(),flap=new ArrayList<>();double xh=.952,zh=.02128173276776986;
void stopGuard()throws Exception{if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Pause requested");}
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
'''
body=body.replace('public void execute()',helpers+'\npublic void execute()',1);target=H/'macros/PrepareStaticPlus2.java';target.write_text(header+body,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(target)],capture_output=True,text=True)
print(r.stdout,r.stderr);assert r.returncode==0;print('STATIC_PREPARATION_COMPILED_NOT_RUN')
