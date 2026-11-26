from pathlib import Path
import subprocess
H=Path(__file__).resolve().parents[1]
src=(H/'macros/C0URANSTopDirection.java').read_text();pre=src[:src.index('public void execute()')].replace('class C0URANSTopDirection','class BenchmarkStaticPlus2')
body=r'''
public void execute(){s=getActiveSimulation();variant="SP_C";Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();out=root.resolve("cases/SP_C_split0_overset/plus2_benchmark_"+System.getenv("NTNU_HYDRO_RUN_ID"));int done=0;double t0=s.getSolution().getPhysicalTime();
try{
Files.createDirectories(out);guard();
if(!input.equals(root.resolve("cases/SP_C_split0_overset/static_plus2_prepared_20261103_085250/SP_C_plus2_prepared_NOT_SOLVED_2606.sim"))||Math.abs(t0-.67)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11570)throw new IllegalStateException("Exact prepared source/time required");
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
RotatingMotion rot=(RotatingMotion)s.getRegionManager().getRegion("FlapOverset").getValues().get(MotionSpecification.class).getMotion();if(!((RotationAngle)rot.getRotationSpecification()).getRotationAngle().getDefinition().equals("<2 deg>"))throw new IllegalStateException("Constant+2 required");
Vector3 point=rot.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double angle=-Math.toDegrees(Math.atan2(point.z-zh,point.x-xh));if(Math.abs(angle-2)>.001)throw new IllegalStateException("Actual mesh angle mismatch");savedFlapBounds=flapBounds();
List<Boundary> outer=new ArrayList<>();for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof InletBoundary||b.getBoundaryType() instanceof PressureBoundary)outer.add(b);
MassFlowReport mass=s.getReportManager().createReport(MassFlowReport.class);mass.getParts().setObjects(outer);
UserFieldFunction of=field("PLUS2_omega_floor","($OversetCellStatus == 0 && $SpecificDissipationRate <= <1.0001e-10 /s>) ? 1 : 0",new Dimensions()),kf=field("PLUS2_k_floor","($OversetCellStatus == 0 && $TurbulentKineticEnergy <= <1.0001e-10 J/kg>) ? 1 : 0",new Dimensions());
ElementCountReport oc=count("PLUS2 omega floor",of,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh")),kc=count("PLUS2 k floor",kf,.5,1.5,s.getRepresentationManager().getObject("Volume Mesh")),ec=count("PLUS2 overset errors",namedField("Overset Error Status","OversetErrorStatus"),.5,100,s.getRepresentationManager().getObject("Volume Mesh"));
MaxReport visc=s.getReportManager().createReport(MaxReport.class);visc.getParts().setObjects(regions);visc.setFieldFunction(s.getFieldFunctionManager().getFunction("TurbulentViscosityRatio"));
MaxReport speed=s.getReportManager().createReport(MaxReport.class);speed.getParts().setObjects(regions);speed.setFieldFunction(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());
AverageWorkerCommunicationTimeReport comm=s.getReportManager().createReport(AverageWorkerCommunicationTimeReport.class);
TimeStepCpuTimeReport cpu=s.getReportManager().createReport(TimeStepCpuTimeReport.class);TimeStepElapsedTimeReport elapsed=s.getReportManager().createReport(TimeStepElapsedTimeReport.class);
captureFields("readback");captureComparison("readback");auditFull("readback",333939);scene();
Files.writeString(out.resolve("preflight.json"),"{\"time\":0.67,\"iteration\":11570,\"actual_angle_deg\":"+angle+",\"flow_frozen\":false,\"dt\":0.002,\"inner\":40,\"mesh\":333939,\"no_reset\":true,\"initial_CL\":"+rv("HF_CL_hydro")+",\"initial_CD\":"+rv("HF_CD")+",\"initial_Mh\":"+rv("HF_Mh_Nm")+"}");
try(BufferedWriter w=Files.newBufferedWriter(out.resolve("history.csv"));BufferedWriter pw=Files.newBufferedWriter(out.resolve("pressure_zones.csv"))){
w.write("step,time_s,Fx_N,Fz_N,CL_hydro,CD,Mh_Nm,p_absolute_min_Pa,cavitation_margin_Pa,mass_imbalance_relative,omega_floor_cells,k_floor_cells,max_turbulent_viscosity_ratio,overset_error_cells,min_volume_m3,min_cell_quality,min_face_validity,max_speed_m_s,yplus_max,native_iteration,solver_step_seconds,native_step_elapsed,native_step_cpu,worker_communication_before,worker_communication_after,start_epoch_ms,end_epoch_ms,measured,flap_angle_deg,flap_angular_velocity_deg_s\n");pw.write("step,time_s,zone,pabs_Pa,x_m,y_m,z_m\n");
for(int i=1;i<=10;i++){if(Files.exists(root.getParent().resolve("STOP_OWNED_CFD.json"))||Files.exists(root.getParent().resolve("PAUSED_FOR_HOME.json")))throw new IllegalStateException("Pause requested");
double cb=comm.getReportMonitorValue();long epoch=System.currentTimeMillis(),start=System.nanoTime();s.getSimulationIterator().step(1);double seconds=(System.nanoTime()-start)/1e9;long endEpoch=System.currentTimeMillis();done=i;double ca=comm.getReportMonitorValue(),nt=elapsed.getReportMonitorValue(),nc=cpu.getReportMonitorValue(),t=s.getSolution().getPhysicalTime();
if(Math.abs(t-(t0+i*.002))>1e-9)throw new IllegalStateException("Time advance mismatch");
double fx=rv("HF_Fx_N"),fz=rv("HF_Fz_N"),cl=rv("HF_CL_hydro"),cd=rv("HF_CD"),mh=rv("HF_Mh_Nm"),p=Double.POSITIVE_INFINITY;
for(String zone:List.of("fixed","flap","near","gap","liquid_all")){MinReport pr=(MinReport)s.getReportManager().getReport("HF_pabs_"+zone);double pv=pr.getReportMonitorValue();p=Math.min(p,pv);double[] loc=new double[3];for(int j=0;j<3;j++)loc[j]=pr.getCollocatedValue(s.getFieldFunctionManager().getFunction("Position").getComponentFunction(j));pw.write(i+","+t+","+zone+","+pv+","+loc[0]+","+loc[1]+","+loc[2]+"\n");}pw.flush();
double bal=Math.abs(mass.getReportMonitorValue())/10800.,om=oc.getReportMonitorValue(),k=kc.getReportMonitorValue(),v=visc.getReportMonitorValue(),err=ec.getReportMonitorValue(),vol=rv("HF_min_volume"),q=rv("HF_min_quality"),valid=rv("HF_min_face_validity"),u=speed.getReportMonitorValue();
w.write(i+","+t+","+fx+","+fz+","+cl+","+cd+","+mh+","+p+","+(p-2339.214766776897)+","+bal+","+om+","+k+","+v+","+err+","+vol+","+q+","+valid+","+u+","+rv("HF_yplus_max")+","+s.getSimulationIterator().getCurrentIteration()+","+seconds+","+nt+","+nc+","+cb+","+ca+","+epoch+","+endEpoch+","+(i>3)+",2,0\n");w.flush();
if(!Double.isFinite(fx+fz+mh+p+bal+om+k+v+err+vol+q+valid+u)||p<=12339.214766776897||bal>=1e-4||om>0||k>0||v>=99999||err>0||vol<=0||q<=0||valid<.5||u>180)throw new IllegalStateException("Strict pressure/mass/turbulence/mesh guard violated");
checkPose("step_"+i);note("Benchmark step="+i+" time="+t+" solver_seconds="+seconds);
}}
captureFields("final");captureComparison("final");auditFull("final",333939);s.saveState(out.resolve("checkpoint.sim").toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"benchmark_complete\",\"steps\":10,\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"scientific_approved\":false,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());captureFields("failure");captureComparison("failure");auditFull("failure",333939);s.saveState(out.resolve("error_checkpoint.sim").toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"benchmark_failed\",\"steps\":"+done+",\"saved_time_s\":"+s.getSolution().getPhysicalTime()+",\"scientific_approved\":false}");}catch(Exception ex){s.println(ex);}throw new RuntimeException(e);}
}
}
'''
target=H/'macros/BenchmarkStaticPlus2.java';target.write_text(pre+body,encoding='utf8')
r=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(H/'macros/compiled'),str(target)],capture_output=True,text=True)
print(r.stdout,r.stderr);assert r.returncode==0
