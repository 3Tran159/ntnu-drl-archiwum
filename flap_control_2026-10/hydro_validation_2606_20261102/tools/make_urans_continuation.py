from pathlib import Path
h=Path(__file__).resolve().parents[1]
src=(h/'macros/InitializeHydroControl.java').read_text(encoding='utf8')
head=src[:src.index('public void execute(){')]
head=head.replace('public class InitializeHydroControl','public class RunURANSFromSteady')
body=r'''public void execute(){s=getActiveSimulation();variant="SP_C";Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),base=input.getParent();String id=System.getenv("NTNU_HYDRO_RUN_ID");out=base.resolve("urans_from_steady_"+id);try{
if(!input.startsWith(root.resolve("cases/SP_C_split0_overset"))||!input.getFileName().toString().equals("steady_checkpoint.sim"))throw new IllegalStateException("Owned steady checkpoint required");
String parent=Files.readString(base.resolve("initialization_status.json"));if(!parent.contains("steady_initialization_incomplete"))throw new IllegalStateException("Only incomplete steady numerical seed allowed");
Files.createDirectories(out);guard();PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");if(pc.getModelManager().getModel(SteadyModel.class)==null)throw new IllegalStateException("Steady model required");
for(Region r:s.getRegionManager().getRegions())if(pc.equals(r.getPhysicsContinuum())){regions.add(r);for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){if(b.getPresentationName().contains("Hydro_Flap"))flap.add(b);else fixed.add(b);}}
if(regions.size()!=2||flap.isEmpty()||fixed.isEmpty())throw new IllegalStateException("Owned regions missing");
if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();
for(String zone:List.of("fixed","flap","near","gap","liquid_all"))if(!(rv("HF_pabs_"+zone)>12339.214766776897))throw new IllegalStateException("Warm seed pressure screening failed");
if(!(rv("HF_min_volume")>0&&rv("HF_min_quality")>0&&rv("HF_min_face_validity")>.5))throw new IllegalStateException("Warm seed mesh guard failed");
captureFields("retained_steady_seed");steadyResume=true;suspendMotionForSteady();
pc.disableModel(pc.getModelManager().getModel(SteadyModel.class));pc.enable(ImplicitUnsteadyModel.class);
s.getSolution().clearSolution(Solution.Clear.History);
ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);us.getTimeStep().setValue(.0004);us.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
for(SolverStoppingCriterion criterion:s.getSolverStoppingCriterionManager().getObjects()){criterion.setIsUsed(false);if(criterion instanceof InnerIterationStoppingCriterion){criterion.setIsUsed(true);((InnerIterationStoppingCriterion)criterion).setMaximumNumberInnerIterations(15);}}
restoreMotionForUnsteady();captureFields("converted_URANS");
Files.copy(base.resolve("normalization.json"),out.resolve("normalization.json"));
Files.writeString(out.resolve("seed_status.json"),"{\"status\":\"warm_numerical_seed_only\",\"steady_acceptance_passed\":false,\"new_physical_time_experiment\":true,\"fields_and_mesh_retained\":true,\"final_URANS_force_mass_pressure_gates_unchanged\":true,\"training_approved\":false}");
Path ready=out.resolve("URANS_ready_from_steady.sim");s.saveState(ready.toString());note("Retained steady fields as numerical seed; full URANS must pass unchanged physical quality gates");
System.setProperty("NTNU_HYDRO_INPUT_OVERRIDE",ready.toString());
StarScript child=new StarScript(s,Paths.get(System.getenv("NTNU_HYDRO_MACRO_DIR")).resolve("StabilizeHydro.java").toFile());child.play();if(child.getInterruptedByException())throw new IllegalStateException("URANS child failed");
Files.writeString(out.resolve("pipeline_status.json"),Files.readString(out.resolve("stabilize_"+id).resolve("status.json")));
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());s.saveState(out.resolve("error_checkpoint.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
finally{System.clearProperty("NTNU_HYDRO_INPUT_OVERRIDE");}
}}
'''
(h/'macros/RunURANSFromSteady.java').write_text(head+body,encoding='utf8')
p=h/'tools/native_launch.py';s=p.read_text(encoding='utf8')
s=s.replace("'RunStaticAngle.java'}","'RunStaticAngle.java','RunURANSFromSteady.java'}")
# Dependency source compilation/snapshot safely includes unused initializer for this wrapper.
p.write_text(s,encoding='utf8');print('new warm-seed URANS pipeline prepared, not launched')
