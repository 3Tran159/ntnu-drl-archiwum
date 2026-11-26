from pathlib import Path
import subprocess
H=Path(__file__).resolve().parents[1];src=(H/'macros/C0URANSTopDirection.java').read_text()
header=src[:src.index('public class')]
helpers=src[src.index('FieldFunction namedField('):src.index('void captureComparison(')]
helpers=helpers.replace('\n}\nString msg="time="','\ns.getTableManager().removeObjects(t);s.getPartManager().removeObjects(plane);\n}\nString msg="time="')
scene=(H/'macros/CheckHydroMotion.java').read_text();scene=scene[scene.index('void scene()'):scene.index('FieldFunction namedField(')]
body=r'''
public class KinematicPoc333939 extends StarMacro {
Scene proofScene;Simulation s;Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out;List<Region> regions=new ArrayList<>();List<Boundary> fixed=new ArrayList<>(),flap=new ArrayList<>();double xh=.952,zh=.02128173276776986;
void note(String message)throws Exception{s.println("KINEMATIC_POC "+message);Files.writeString(out.resolve("progress.txt"),message+"\n");}
void stopGuard()throws Exception{if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Pause requested");}
public void execute(){s=getActiveSimulation();Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();out=root.resolve("cases/SP_C_split0_overset/kinematic_poc_"+System.getenv("NTNU_HYDRO_RUN_ID"));int completed=0;double t0=s.getSolution().getPhysicalTime();
try{
if(!input.equals(root.resolve("cases/SP_C_split0_overset/relocation_reopen_20261103_082325/C0_recovered_t065.sim")))throw new IllegalStateException("Exact verified C0 recovery source required");
if(!Files.readString(root.resolve("audit/C0_KINEMATIC_BASE_ACCEPTANCE_20261103.json")).contains("\"accepted_for_kinematics\": true"))throw new IllegalStateException("POC baseline gate not passed");
if(Math.abs(t0-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560||s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Source counters or CPU guard");
Files.createDirectories(out);stopGuard();s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
Region bg=s.getRegionManager().getRegion("Background"),ov=s.getRegionManager().getRegion("FlapOverset");regions.add(bg);regions.add(ov);
for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(r==ov)flap.add(b);else fixed.add(b);}
RotatingMotion rot=(RotatingMotion)ov.getValues().get(MotionSpecification.class).getMotion();
if(!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<0 deg>"))throw new IllegalStateException("Source flap not at constant zero");
double oldCL=s.getReportManager().getReport("HF_CL_hydro").getReportMonitorValue();if(Math.abs(oldCL-.3256530206195925)>1e-8)throw new IllegalStateException("Source force readback mismatch");
auditFull("initial",333939);
AreaAverageReport[] center=new AreaAverageReport[3];double[] initialCenter=new double[3];
for(int j=0;j<3;j++){center[j]=s.getReportManager().createReport(AreaAverageReport.class);center[j].getParts().setObjects(flap);center[j].setFieldFunction(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));initialCenter[j]=center[j].getReportMonitorValue();}
((RotationAngle)rot.getRotationSpecification()).getRotationAngle().setDefinition("<5 deg>*sin(2*3.141592653589793*($Time - <"+t0+" s>)/<0.2 s>)");
StringBuilder frozen=new StringBuilder();for(Solver solver:s.getSolverManager().getObjects())if(solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb")){solver.setFrozen(true);frozen.append(solver.getClass().getName()+"\n");}
Files.writeString(out.resolve("frozen_solvers.txt"),frozen.toString());
s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(.002);
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(1);}}
scene();Scene sc=proofScene;sc.setPresentationName("Kinematics ONLY - flow frozen");sc.getCurrentView().setInput(new DoubleVector(new double[]{1.035,.02,.02}),new DoubleVector(new double[]{1.035,-3,.02}),new DoubleVector(new double[]{0,0,1}),.22,1,s.getCoordinateSystemManager().getLabCoordinateSystem(),false);sc.printAndWait(out.resolve("frame_000.png").toString(),1,1100,800);
s.saveState(out.resolve("kinematic_ready.sim").toString());
double minVolume=Double.POSITIVE_INFINITY,minQuality=1,maxAngleError=0,maxCenterError=0;
try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv")))){
w.write("step,time_s,flap_angle_deg,flap_angular_velocity_deg_s,measured_deg,angle_error_deg,center_error_m,min_volume_m3,min_cell_quality,min_face_validity,overset_error_cells,difficult_interpolation_cells,flow_frozen\n");
for(int k=1;k<=100;k++){
stopGuard();s.getSimulationIterator().step(1);completed=k;double t=s.getSolution().getPhysicalTime();if(Math.abs(t-(t0+.002*k))>1e-9)throw new IllegalStateException("Unexpected time advance");
double phase=2*Math.PI*(t-t0)/.2,cmd=5*Math.sin(phase),omega=5*2*Math.PI/.2*Math.cos(phase),a=Math.toRadians(cmd);
Vector3 point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double actual=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh));
double dx=initialCenter[0]-xh,dz=initialCenter[2]-zh;double[] expected={xh+dx*Math.cos(a)+dz*Math.sin(a),initialCenter[1],zh-dx*Math.sin(a)+dz*Math.cos(a)};double centerError=0;
for(int j=0;j<3;j++)centerError=Math.max(centerError,Math.abs(center[j].getReportMonitorValue()-expected[j]));
auditFull("step_"+k,333939);
double v=s.getReportManager().getReport("HF_min_volume").getReportMonitorValue(),q=s.getReportManager().getReport("HF_min_quality").getReportMonitorValue(),face=s.getReportManager().getReport("HF_min_face_validity").getReportMonitorValue();
minVolume=Math.min(minVolume,v);minQuality=Math.min(minQuality,q);maxAngleError=Math.max(maxAngleError,Math.abs(actual-cmd));maxCenterError=Math.max(maxCenterError,centerError);
w.write(String.format(Locale.ROOT,"%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,0,0,true\n",k,t,cmd,omega,actual,actual-cmd,centerError,v,q,face));w.flush();
if(!(v>0&&q>0&&face>.9&&Double.isFinite(actual+centerError))||Math.abs(actual-cmd)>.01||centerError>1e-7)throw new IllegalStateException("Motion/mesh guard failed at step"+k);
if(k%5==0)sc.printAndWait(out.resolve(String.format(Locale.ROOT,"frame_%03d.png",k/5)).toString(),1,1100,800);
if(k%25==0){s.saveState(out.resolve("checkpoint_step_"+k+".sim").toString());note("step="+k+" angle="+cmd+" full_overset_errors=0");}
}}
Files.writeString(out.resolve("NOT_A_HYDRODYNAMIC_RESTART.txt"),"Frozen-flow kinematic sweep only. Flow fields not advanced or converged at moving positions. Do not use forces or time history as hydrodynamic data. For +2degree hydrodynamics use original verified C0t0.650 checkpoint, not this file. Flow and turbulence solvers intentionally remain frozen in this demonstrator. No mesh regeneration or solution reset performed.");
s.saveState(out.resolve("motion_verified.sim").toString());
Files.writeString(out.resolve("status.json"),"{\"status\":\"kinematic_poc_passed\",\"steps\":"+completed+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"hydrodynamics_solved\":false,\"flow_frozen\":true,\"min_volume_m3\":"+minVolume+",\"min_quality\":"+minQuality+",\"max_angle_error_deg\":"+maxAngleError+",\"max_center_error_m\":"+maxCenterError+",\"all_full_overset_audits_passed\":true,\"training_approved\":false}");note("KINEMATICS_PASSED_FLOW_NOT_SOLVED");
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"kinematic_poc_failed\",\"steps\":"+completed+",\"time_s\":"+s.getSolution().getPhysicalTime()+",\"training_approved\":false}");s.saveState(out.resolve("motion_error.sim").toString());}catch(Exception secondary){s.println("SAVE_ERROR "+secondary);}throw new RuntimeException(e);}
}
}
'''
body=body.replace('try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"))))','try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv")))')
body=body.replace('public void execute()',helpers+'\n'+scene+'\npublic void execute()',1)
target=H/'macros/KinematicPoc333939.java';target.write_text(header+body,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(target)],capture_output=True,text=True)
print(r.stdout,r.stderr);assert r.returncode==0;print('KINEMATIC_POC_COMPILED')
