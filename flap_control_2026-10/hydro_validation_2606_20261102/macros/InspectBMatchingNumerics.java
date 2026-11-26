package macro;
import star.common.*;import star.segregatedflow.*;import star.kwturb.*;import star.flow.*;import star.turbulence.*;import star.base.report.*;import java.nio.file.*;import java.util.*;import java.io.*;
public class InspectBMatchingNumerics extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path h=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),out=h.resolve("audit/matching_B_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{Path input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();if(!input.equals(h.resolve("cases/SP_B_split0_fixed/SP_B_split0_stabilized_2606.sim")))throw new IllegalStateException("Exact task B reference required");
Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
double time=s.getSolution().getPhysicalTime();int iteration=s.getSimulationIterator().getCurrentIteration();
PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");
SegregatedFlowSolver flow=s.getSolverManager().getSolver(SegregatedFlowSolver.class);ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
StringBuilder b=new StringBuilder("source="+input+"\nphysical_time_s="+time+"\nnative_iteration="+iteration+"\n");
b.append("velocity_urf="+flow.getVelocitySolver().getUrf()+"\npressure_urf="+flow.getPressureSolver().getUrf()+"\ndynamic_velocity_urf="+flow.getVelocitySolver().getUseDynamicLocalUrf()+"\ncontinuity_initialization="+flow.getContinuityInitialization()+"\n");
b.append("flow_convection="+pc.getModelManager().getModel(SegregatedFlowModel.class).getUpwindOption().getSelected()+"\nflow_SECOND_ORDER="+FlowUpwindOption.Type.SECOND_ORDER.getValue()+"\n");
b.append("SST_convection="+pc.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().getSelected()+"\nSST_SECOND_ORDER="+UpwindOption.Type.SECOND_ORDER.getValue()+"\n");
b.append("dt_s="+us.getTimeStep().getValue()+"\ntime_discretization="+us.getTimeDiscretizationOption().getSelected()+"\ntime_SECOND_ORDER="+TimeDiscretizationOption.Type.SECOND_ORDER.getValue()+"\n");
for(SolverStoppingCriterion c:s.getSolverStoppingCriterionManager().getObjects())if(c instanceof InnerIterationStoppingCriterion)b.append("inner_iterations="+((InnerIterationStoppingCriterion)c).getMaximumNumberInnerIterations()+" used="+c.getIsUsed()+"\n");
for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor){ResidualMonitor r=(ResidualMonitor)m;b.append("residual="+r.getPresentationName()+" normalized="+r.isNormalized()+" factor="+r.getNormalizationType().getNormalizationFactor()+"\n");r.export(out.resolve("residual_"+r.getPresentationName().replaceAll("[^A-Za-z0-9_-]","_")+".csv").toString());}
for(String name:List.of("HF_Fx_N","HF_Fz_N","HF_CL_hydro","HF_CD","HF_Mh_Nm","HF_pabs_liquid_all","HF_min_volume","HF_min_quality"))b.append(name+"="+s.getReportManager().getReport(name).getReportMonitorValue()+"\n");
for(Region r:s.getRegionManager().getRegions())for(Boundary boundary:r.getBoundaryManager().getBoundaries())if(boundary.getBoundaryType() instanceof PressureBoundary){b.append("boundary="+boundary.getPresentationName()+"\n");for(Object c:boundary.getConditions().getObjects())if(c instanceof EnumeratedOption)b.append(" option="+c.getClass().getSimpleName()+" selected="+((EnumeratedOption)c).getSelected()+"\n");}
Files.writeString(out.resolve("matching_numerics.txt"),b.toString());
if(s.getSolution().getPhysicalTime()!=time||s.getSimulationIterator().getCurrentIteration()!=iteration)throw new IllegalStateException("Read-only audit advanced solution");
Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"simulation_saved\":false,\"physical_time_preserved\":true,\"training_approved\":false}");
}catch(Exception e){try{Files.createDirectories(out);Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
