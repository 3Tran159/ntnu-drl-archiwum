package macro;
import star.common.*;
import star.vof.*;
import star.flow.*;
import java.nio.file.*;
import java.util.*;

/** Diagnostic only; edits live memory and never saves built.sim. */
public class WaveTankDiagnose extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  try{
   Path target=Paths.get("F:/ntnu/wave_depth_20261029/W20_H16_X3/built.sim").toAbsolutePath().normalize();
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(target))throw new IllegalStateException("bad input");
   s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   s.getSimulationIterator().getAutoSave().setEnabled(false);
   String which=System.getenv("NTNU_WAVE_DIAG_VARIANT");
   if(which==null)which="zone_none";
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   VofWaveModel model=(VofWaveModel)pc.getModelManager().getModel(VofWaveModel.class);
   FirstOrderVofWave w=null;for(ManagedVofWave q:model.getVofWaveManager().getObjects())if(q instanceof FirstOrderVofWave)w=(FirstOrderVofWave)q;if(w==null)throw new IllegalStateException("FirstOrder wave missing");
   s.println("[NTNU_DIAG] variant="+which+" deep="+w.getDeepWaterApproximation()+" length="+w.getVofWaveSpecification().getWaveLength().getSIValue()+" h="+w.getVofWaveDepthSpecification().getWaterDepth().getSIValue()+" amp="+w.getAmplitude().getSIValue());
   Region region=s.getRegionManager().getRegion("fluid");
   if(which.startsWith("zone_none")||which.equals("flat_only")){
     region.getConditions().get(VofWaveZoneOption.class).setSelected(VofWaveZoneOptionEnum.NONE);
   }
   if(which.equals("flat_only")){
     FlatVofWave calm=(FlatVofWave)model.getVofWaveManager().getVofWave("Calm");
     FieldFunctionManager ff=s.getFieldFunctionManager();
     pc.getInitialConditions().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(ff.getFunction("VelocityWave0"));
     pc.getInitialConditions().get(InitialPressureProfile.class).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(ff.getFunction("HydrostaticPressureWave0"));
     pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(ff.getFunction("VolumeFractionHeavyFluidWave0"));
     Boundary inlet=region.getBoundaryManager().getBoundary("DOMAIN.inlet"),outlet=region.getBoundaryManager().getBoundary("DOMAIN.outlet");
     inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(ff.getFunction("VelocityWave0"));
     inlet.getValues().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(ff.getFunction("VolumeFractionHeavyFluidWave0"));
     outlet.getValues().get(StaticPressureProfile.class).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(ff.getFunction("HydrostaticPressureWave0"));
   }
   if(which.equals("new_length")){
     w.getVofWaveSpecification().getWaveLength().setValue(20);
   }
   if(which.equals("deep")){
     w.setDeepWaterApproximation(true);
   }
   s.println("[NTNU_DIAG] initializing");
   s.getSolution().initializeSolution();
   s.println("[NTNU_DIAG] SUCCESS initialized variant="+which);
   Files.writeString(Paths.get("F:/ntnu/wave_depth_20261029/diagnose_"+which+"_ok.txt"),"success");
  }catch(Exception e){throw new RuntimeException("[NTNU_DIAG] "+e.toString(),e);}
 }
}
