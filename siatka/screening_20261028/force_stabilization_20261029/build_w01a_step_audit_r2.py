from pathlib import Path
R=Path("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
s=(R/"AuditW01aInletRampR1.java").read_text()
s=s[:s.index(" public void execute()")]
s=s.replace("AuditW01aInletRampR1","AuditW01aInletRampStepR2").replace("Disposable CPU1 zero-flow audit only. Never initialize, clear, or step solution.","Disposable CPU1 bounded three-step runtime cache audit. Never initialize or clear solution.")
s+=r'''
 private boolean finite(Object x){if(x instanceof Number)return Double.isFinite(((Number)x).doubleValue());if(x instanceof Map){for(Object v:((Map<?,?>)x).values())if(!finite(v))return false;}if(x instanceof List){for(Object v:(List<?>)x)if(!finite(v))return false;}return x!=null;}
 public void execute(){
  s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_W01A_RAMP_AUDIT_OUT")));int done=0;
  try{
   double origin=s.getSolution().getPhysicalTime(),dt=.001,duration=2*.8472673206891129;
   if(s.getNumberOfGpgpus()!=0||Math.abs(origin-.587)>1e-10)throw new IllegalStateException("Requires CPU/noGPU computed calm t.587 final");
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable copy required");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");if(fv.getCellCount()!=317277)throw new IllegalStateException("Mesh differs");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   Map<String,Object> before=physicalFingerprint();write("physical_before.json",before);
   FieldFunction omega=null;for(Object o:s.getFieldFunctionManager().getVectorFieldFunctions())if(o instanceof VorticityVectorFunction)omega=(FieldFunction)o;
   if(omega==null)throw new IllegalStateException("Native vorticity missing");
   write("native_vorticity_lookup.json",Map.of("function_name",omega.getFunctionName(),"class",omega.getClass().getName(),"component_index",1));
   PhysicsContinuum pc=reg.getPhysicsContinuum();VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);wm.setEnableTheoryComparison(true);
   FifthOrderVofWave expressionWave=makeWave(wm,"W01a_Ramp_Runtime_Audit"),constantWave=makeWave(wm,"W01a_Constant_Runtime_Audit");
   expressionWave.getWaveHeight().setDefinition(rampExpression(origin,duration));constantWave.getWaveHeight().setValue(.000001);
   Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet");
   inlet.getValues().get(VelocityProfile.class).setMethod(FunctionVectorProfileMethod.class);
   inlet.getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).setFieldFunction(waveField(expressionWave,"Velocity of "));
   VolumeFractionProfile vp=inlet.getValues().get(VolumeFractionProfile.class);vp.setMethod(CompositeNMinus1ArrayProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);vp.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(waveField(expressionWave,"Volume Fraction of Heavy Fluid of "));
   reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(expressionWave);
   ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-dt)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("Requires existing SO1ms");
   for(Object x:s.getSolverStoppingCriterionManager().getChildren()){if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);((SolverStoppingCriterion)x).setIsUsed(true);}}
   ArrayList<PlaneSection> gauges=new ArrayList<>();for(double x:new double[]{-34.99,-25,-15,-10,-5,0,5,10}){PlaneSection p=s.getPartManager().createPlaneSection();p.setPresentationName("Runtime audit gauge x"+x);p.getInputParts().setObjects(reg);p.setOrigin(new DoubleVector(new double[]{x,.02,0}));p.setOrientation(new DoubleVector(new double[]{1,0,0}));gauges.add(p);}
   Map<String,Object> configured=physicalFingerprint();boolean unchanged=true;for(String k:before.keySet()){double a=((Number)before.get(k)).doubleValue(),b=((Number)configured.get(k)).doubleValue();if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a-b)>1e-10*Math.max(1,Math.abs(a)))unchanged=false;}
   write("configuration_fingerprint.json",Map.of("before",before,"after",configured,"unchanged",unchanged));if(!unchanged)throw new IllegalStateException("Configuration changed physical fields");
   ArrayList<Object> rows=new ArrayList<>();
   for(int i=1;i<=3;i++){
    if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL")))throw new IllegalStateException("Stop marker");
    double expected=.000001+.499999*.5*(1-Math.cos(Math.PI*(i*dt)/duration));constantWave.getWaveHeight().setValue(expected);
    s.getSimulationIterator().step(1);done=i;double t=s.getSolution().getPhysicalTime();
    Map<String,Object> phys=physicalFingerprint(),exp=analytical(expressionWave,gauges,inlet),con=analytical(constantWave,gauges,inlet),row=new LinkedHashMap<>();
    double ed=maxListDiff(exp.get("analytic_gauge_eta_m"),con.get("analytic_gauge_eta_m")),vd=maxListDiff(exp.get("analytic_inlet_mean_velocity_m_s"),con.get("analytic_inlet_mean_velocity_m_s"));
    double period=((Number)exp.get("period_s")).doubleValue();boolean pp=finite(phys)&&((Number)phys.get("max_speed_m_s")).doubleValue()<50&&((Number)phys.get("alpha_min")).doubleValue()>=-1e-8&&((Number)phys.get("alpha_max")).doubleValue()<=1+1e-8&&Math.abs(t-origin-i*dt)<1e-10;
    boolean ap=finite(exp)&&period>0&&Math.abs(((Number)exp.get("height_m")).doubleValue()-expected)<1e-10;
    row.put("step",i);row.put("time_s",t);row.put("expected_height_m",expected);row.put("physical",phys);row.put("expression",exp);row.put("constant",con);row.put("max_gauge_difference_m",ed);row.put("max_mean_velocity_difference_m_s",vd);row.put("physical_guard_pass",pp);row.put("analytic_finite_pass",ap);
    row.put("native_water_error_kg_step",s.getReportManager().getReport("Inspect_NativeWater_MassConservationError").getReportMonitorValue());row.put("native_air_error_kg_step",s.getReportManager().getReport("Inspect_NativeAir_MassConservationError").getReportMonitorValue());
    rows.add(row);write("guarded_step_results.json",rows);
    if(!pp||!ap)throw new IllegalStateException("First/runtime guarded step failed physical="+pp+" analytic="+ap);
   }
   exportPhysical("physical_fields.csv",omega);s.saveState(out.resolve("final.sim").toString());
   write("audit.json",Map.of("status","three_guarded_steps_completed","flow_steps",done,"time_s",s.getSolution().getPhysicalTime(),"source_time_s",origin,"configuration_fingerprint_unchanged",unchanged,"initialized_or_cleared",false,"gpu_count",0,"guarded_steps",rows,"note","Three near-zero-height runtime steps test immediate cache readiness only. They do not validate full-height nonlinear ramp refresh or wave-force accuracy."));
  }catch(Exception e){try{write("audit_error.json",Map.of("error",e.toString(),"time_s",s.getSolution().getPhysicalTime(),"flow_steps",done));s.saveState(out.resolve("error_preserved.sim").toString());}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}
'''
(R/"AuditW01aInletRampStepR2.java").write_text(s)
p=(R/"run_w01a_inlet_ramp_api_audit_r1.py").read_text().replace("run_w01a_inlet_ramp_api_audit","run_w01a_inlet_ramp_step_audit").replace("w01a_inlet_ramp_api_audit","w01a_inlet_ramp_step_audit").replace("W01a_inlet_ramp_api_audit_r1","W01a_inlet_ramp_step_audit_r2").replace("AuditW01aInletRampR1","AuditW01aInletRampStepR2").replace("checkpoint_startup_t0.020.sim","final.sim")
p=p.replace('".step("','".run("').replace("physical_time_s=.02","physical_time_s=.587").replace("flow_steps=0","maximum_flow_steps=3").replace('result.get("physical_fields_fingerprint_unchanged")','result.get("configuration_fingerprint_unchanged")').replace('result.get("flow_steps")!=0','result.get("flow_steps")!=3')
p=p.replace("zero-step","bounded three-step").replace("zero_step","bounded_step").replace("noFlow","max3flowsteps").replace("Never runs CFD iterations.","Maximum three guarded CFD time steps.")
p=p.replace('if not SOURCE.is_file():raise RuntimeError("Computed source checkpoint missing")','if not SOURCE.is_file():raise RuntimeError("Computed source checkpoint missing")\n completed=e.read(SOURCE.parent/"completed.json",{})\n if completed.get("status")!="stopped_by_marker" or abs(completed.get("time_s",0)-.587)>1e-10:raise RuntimeError("Source must be completed W01a t.587")')
(R/"run_w01a_inlet_ramp_step_audit_r2.py").write_text(p)
import ast
ast.parse(p)
print("Generated standalone R2 macro/controller; not launched.")
