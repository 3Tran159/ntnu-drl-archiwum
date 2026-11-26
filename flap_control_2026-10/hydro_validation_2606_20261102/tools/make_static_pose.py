from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
src=(h/'macros/CheckHydroMotion.java').read_text(encoding='utf8')
t=src[:src.index('PhysicsContinuum physics()')].replace('class CheckHydroMotion','class PrepareStaticFlap')
t+=src[src.index('void scene()'):src.index('public void execute()')]
t+='''public void execute(){s=getActiveSimulation();variant="SP_C";Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),base=input.getParent();String id=System.getenv("NTNU_HYDRO_RUN_ID");double angle=Double.parseDouble(System.getenv("NTNU_HYDRO_ANGLE_DEG"));List<Solver> frozen=new ArrayList<>();out=root.resolve("cases/SP_C_split0_overset/static_"+(angle<0?"minus":"plus")+Math.round(Math.abs(angle))+"_"+id);
try{if(!input.startsWith(root.resolve("cases/SP_C_split0_overset"))||!List.of(2.,-2.,5.,-5.).contains(angle))throw new IllegalStateException("Approved static pose and owned SP_C required");Files.createDirectories(out);guard();String parentStatus=Files.readString(base.resolve("status.json"));if(!parentStatus.contains("force_stabilization_passed"))throw new IllegalStateException("Parent static stabilization must pass before next angle");
Region bg=s.getRegionManager().getRegion("Background"),ov=s.getRegionManager().getRegion("FlapOverset");regions.add(bg);regions.add(ov);for(Region r:regions)for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(r==ov)flap.add(b);else fixed.add(b);}
RotatingMotion rotation=(RotatingMotion)ov.getValues().get(MotionSpecification.class).getMotion();if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();double t0=s.getSolution().getPhysicalTime();
for(Solver solver:s.getSolverManager().getObjects())if(solver instanceof SegregatedFlowSolver||solver.getClass().getName().toLowerCase(Locale.ROOT).contains("turb"))if(!solver.getFrozen()){solver.setFrozen(true);frozen.add(solver);}
((RotationAngle)rotation.getRotationSpecification()).getRotationAngle().setDefinition("<"+angle+" deg>");s.getSolverManager().getSolver(ImplicitUnsteadySolver.class).getTimeStep().setValue(.0004);for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects()){c.setIsUsed(false);if(c instanceof InnerIterationStoppingCriterion){c.setIsUsed(true);((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(1);}}
s.getSimulationIterator().step(1);
Vector3 measured=rotation.transformInitialCoordinate(new Vector3(xh+.2,.02,zh));double actual=-Math.toDegrees(Math.atan2(measured.z-zh,measured.x-xh));Representation rep=(Representation)s.getRepresentationManager().getObject("Overset Mesh");ElementCountReport errors=count("Static pose connectivity errors",namedField("Overset Error Status","OversetErrorStatus"),.5,100,rep);double err=errors.getReportMonitorValue();if(Math.abs(actual-angle)>.01||err!=0||!(s.getReportManager().getReport("HF_min_volume").getReportMonitorValue()>0&&s.getReportManager().getReport("HF_min_quality").getReportMonitorValue()>0))throw new IllegalStateException("Static pose geometry/connectivity check failed");
for(Solver solver:frozen)solver.setFrozen(false);for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())if(c instanceof InnerIterationStoppingCriterion)((InnerIterationStoppingCriterion)c).setMaximumNumberInnerIterations(15);
Files.copy(base.resolve("normalization.json"),out.resolve("normalization.json"));Files.writeString(out.resolve("pose.json"),"{\\"target_angle_deg\\":"+angle+",\\"measured_angle_deg\\":"+actual+",\\"overset_error_cells\\":"+err+",\\"source_time_s\\":"+t0+",\\"pose_step_flow_frozen\\":true,\\"training_approved\\":false}");scene();s.saveState(out.resolve("pose_ready.sim").toString());note("Pose verified; warm fields require new numerical initialization and stabilization");
}catch(Exception e){for(Solver solver:frozen)solver.setFrozen(false);try{Files.writeString(out.resolve("pose_error.txt"),e.toString());s.saveState(out.resolve("pose_error.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}}
}
'''
(h/'macros/PrepareStaticFlap.java').write_text(t,encoding='utf8')
p=h/'tools/native_launch.py';l=p.read_text(encoding='utf8')
l=l.replace("'RepairOversetExtrusion.java'}","'RepairOversetExtrusion.java','PrepareStaticFlap.java'}",1)
needle="env={**os.environ,'NTNU_HYDRO_ROOT':str(R),'NTNU_HYDRO_VARIANT':variant,'NTNU_HYDRO_RUN_ID':stamp}"
l=l.replace(needle,needle+"""
if macro.name=='PrepareStaticFlap.java':
 angle=float(sys.argv[4]);assert angle in [2.,-2.,5.,-5.]
 env['NTNU_HYDRO_ANGLE_DEG']=str(angle)
""")
p.write_text(l,encoding='utf8')
print('Static pose macro prepared; mandatory previous stabilization gate')
