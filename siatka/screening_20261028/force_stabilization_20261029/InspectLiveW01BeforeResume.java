package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.vof.*;import star.segregatedflow.*;import java.nio.file.*;import java.util.*;
public class InspectLiveW01BeforeResume extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/live_w01_resume_audit.json");
  try{
   Region r=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);
   FifthOrderVofWave w=(FifthOrderVofWave)r.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();
   double t=s.getSolution().getPhysicalTime(),dt=us.getTimeStep().getValue();long cells=fv.getCellCount();int inner=0;
   for(Object x:s.getSolverStoppingCriterionManager().getChildren())if(x instanceof InnerIterationStoppingCriterion)inner=((InnerIterationStoppingCriterion)x).getMaximumNumberInnerIterations();
   double p=s.getSolverManager().getSolver(SegregatedFlowSolver.class).getPressureSolver().getAMGLinearSolver().getConvergeTol();
   if(Math.abs(t-.168)>1e-9||Math.abs(dt-.001)>1e-12||cells!=317277||s.getNumberOfGpgpus()!=1||inner!=10||Math.abs(p-.01)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER")||Math.abs(w.getWaveHeight().getValue()-.5)>1e-8||Math.abs(w.getVofWaveSpecification().getWaveLength().getValue()-20)>1e-6||Math.abs(w.getWaterDepth().getValue()-24)>1e-8||w.getFirstWaveFront())throw new IllegalStateException("Live state differs from expected saved W01");
   String path=s.getSessionPath().replace("\\","/").replace("\"","");
   String json="{\"status\":\"live_saved_W01_identity_passed\",\"time_s\":"+t+",\"dt_s\":"+dt+",\"inner\":"+inner+",\"cells\":"+cells+",\"gpu\":"+s.getNumberOfGpgpus()+",\"period_s\":"+w.getWavePeriod().getValue()+",\"session_path\":\""+path+"\",\"current\":\""+w.getCurrentVector()+"\",\"direction\":\""+w.getAdvancingDirectionVector()+"\",\"steps_taken\":0}";
   Files.writeString(out,json);s.println("LIVE_W01_RESUME_IDENTITY_PASSED t="+t);
  }catch(Exception ex){try{Files.writeString(out,"{\"status\":\"failed\",\"error\":\""+ex.toString().replace("\\","/").replace("\"","'")+"\"}");}catch(Exception ignored){}throw new RuntimeException(ex);}
 }
}
