package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.post.*;
import java.nio.file.*;import java.util.*;
public class WaveInner40PhaseProbeR11 extends StarMacro {
 private Simulation s;private Path out;private Region reg;private FvRepresentation fv;
 private String json(Object o){
  if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Map.Entry<?,?> e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
  if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Iterable<?>)o)j.add(json(a));return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
 private MaxReport max(String name,FieldFunction ff,NamedObject part){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setPresentationName(name);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(part);r.createMonitor();return r;}
 private SurfaceIntegralReport integral(PlaneSection p,FieldFunction ff){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(p);r.setSmooth(false);return r;}

 private Continuum phase(PhysicsContinuum pc,String name)throws Exception{
  for(Object model:pc.getModelManager().getChildren()){
   try{
    Object pm=model.getClass().getMethod("getPhaseManager").invoke(model);
    Object ph=pm.getClass().getMethod("getPhase",String.class).invoke(pm,name);
    if(ph instanceof Continuum)return (Continuum)ph;
   }catch(NoSuchMethodException ignored){}
  }
  throw new IllegalStateException("Required Eulerian phase not found: "+name);
 }
 private MassConservationErrorReport nativeError(String name,Continuum phase){
  MassConservationErrorReport r=s.getReportManager().createReport(MassConservationErrorReport.class);
  r.setPresentationName(name);r.setPhase(phase);r.setRepresentation(fv);r.setSmooth(false);r.getParts().setObjects(reg);
  r.setUnits((Units)s.getUnitsManager().getObject("kg"));
  if(!r.getPhase().equals(phase))throw new IllegalStateException("Native phase report binding mismatch");
  return r;
 }
 private Object getter(Object o,String method){
  try{Object value=o.getClass().getMethod(method).invoke(o);return value==null?null:value.toString();}
  catch(Exception ex){return "UNAVAILABLE:"+ex.getClass().getSimpleName();}
 }
 private Map<String,Object> nativeDefinition(MassConservationErrorReport r){
  Map<String,Object>d=new LinkedHashMap<>();d.put("name",r.getPresentationName());d.put("phase",r.getPhase().getPresentationName());
  d.put("units",r.getUnits().toString());d.put("representation",String.valueOf(r.getRepresentation()));d.put("parts",r.getParts().getObjects().toString());d.put("smooth",r.getSmooth());
  d.put("meaning","Native phase transport mass imbalance summed over cells and multiplied by the physical time step; kg per step. Independent iteration-error diagnostic, not a replacement for the inventory-plus-boundary-flux diagnostic.");
  return d;
 }

 public void execute(){s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_OUT")));
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable input copy required");
   if(Files.exists(out.resolve("history.csv")))throw new IllegalStateException("Attempt already used");
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");
   double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));
   if(Math.abs(dt-.001)>1e-12||steps!=250)throw new IllegalStateException("R11 requires exactly 1 ms and 250 steps");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()!=Long.parseLong(System.getenv("NTNU_WAVE_CELLS"))||Math.abs(s.getSolution().getPhysicalTime()-.5)>1e-8)throw new IllegalStateException("Input state mismatch");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
   for(Object x:s.getSolverStoppingCriterionManager().getChildren()){
    if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
    if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(40);((SolverStoppingCriterion)x).setIsUsed(true);}
   }
   ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);if(Math.abs(us.getTimeStep().getValue()-dt)>1e-12||!String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()).equals("SECOND_ORDER"))throw new IllegalStateException("R11 must retain checkpoint SO 1 ms settings");
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   FifthOrderVofWave wave=(FifthOrderVofWave)reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();
   if(!Boolean.FALSE.equals(wave.getClass().getMethod("getFirstWaveFront").invoke(wave))||Math.abs(wave.getWaterDepth().getValue()-24)>1e-8)throw new IllegalStateException("Wave scope mismatch");
   double initialTime=s.getSolution().getPhysicalTime();
   Boundary outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet"),bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom");
   if(!String.valueOf(outlet.getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()).equals("ENVIRONMENTAL")||!String.valueOf(bed.getConditions().get(WallShearStressOption.class).getSelectedElement()).equals("SLIP"))throw new IllegalStateException("Checkpoint boundary settings mismatch");
   Files.writeString(out.resolve("continuation_identity.json"),json(Map.of("initial_time_s",initialTime,"target_time_s",.75,"reinitialized",false,"outlet_backflow","ENVIRONMENTAL","bottom","SLIP","scope","Matched phase transport diagnostic; only 10 to 40 inner iterations relative to R4, SO1ms unchanged; no initialization or boundary changes; not propagation acceptance")));
   FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
   FieldFunction theory=pc.getInitialConditions().get(VolumeFractionProfile.class).getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).getFieldFunction();
   FieldFunction one=s.getFieldFunctionManager().getFunction("PropagationUnit");
   double[] xs={-10,-5,0,2.5,5,10,15,20};
   ArrayList<SurfaceIntegralReport> actual=new ArrayList<>(),analytic=new ArrayList<>();
   for(double x:xs){PlaneSection p=s.getPartManager().createPlaneSection();p.getInputParts().setObjects(reg);p.setOrigin(new DoubleVector(new double[]{x,20.01,2}));p.setOrientation(new DoubleVector(new double[]{1,0,0}));actual.add(integral(p,alpha));analytic.add(integral(p,theory));
    SurfaceIntegralReport ar=s.getReportManager().createReport(SurfaceIntegralReport.class);ar.setFieldFunction(one);ar.setRepresentation(fv);ar.getParts().setObjects(p);if(Math.abs(ar.getReportMonitorValue()/.02-30)>.0001)throw new IllegalStateException("Gauge area mismatch at "+x);
   }
   MaxReport vmax=max("Wave_MaxSpeed",s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction(),reg),cfl=max("Wave_MaxCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),reg),amax=max("Wave_MaxAlpha",alpha,reg);
   MinReport amin=s.getReportManager().createReport(MinReport.class);amin.setRepresentation(fv);amin.setFieldFunction(alpha);amin.getParts().setObjects(reg);
   ThresholdPart inter=s.getPartManager().createThresholdPart();inter.getInputParts().setObjects(reg);inter.setFieldFunction(alpha);inter.setRange(new DoubleVector(new double[]{.01,.99}));inter.setMode(ThresholdMode.BETWEEN_TAG);
   MaxReport icfl=max("Wave_InterfaceCFL",s.getFieldFunctionManager().getFunction("CourantNumber"),inter);
   VolumeIntegralReport mass=s.getReportManager().createReport(VolumeIntegralReport.class);mass.setRepresentation(fv);mass.setFieldFunction(s.getFieldFunctionManager().getFunction("Density"));mass.getParts().setObjects(reg);
   VolumeIntegralReport water=s.getReportManager().createReport(VolumeIntegralReport.class);water.setRepresentation(fv);water.setFieldFunction(alpha);water.getParts().setObjects(reg);
   ArrayList<String> fluxNames=new ArrayList<>();ArrayList<MassFlowReport> flux=new ArrayList<>();for(Boundary b:reg.getBoundaryManager().getBoundaries()){MassFlowReport r=s.getReportManager().createReport(MassFlowReport.class);r.getParts().setObjects(b);r.setRepresentation(fv);flux.add(r);fluxNames.add(b.getPresentationName());}
   Files.writeString(out.resolve("setup.json"),json(Map.of("cells",fv.getCellCount(),"dt_s",dt,"inner",40,"order","SECOND_ORDER","wave_period_s",wave.getWavePeriod().getValue(),"steps",steps,"gpu_count",s.getNumberOfGpgpus(),"scope","40-inner phase budget diagnostic; original0.01%gate retained; no force or final propagation acceptance")));
   VolumeIntegralReport analyticWater=s.getReportManager().createReport(VolumeIntegralReport.class);analyticWater.setRepresentation(fv);analyticWater.setFieldFunction(theory);analyticWater.getParts().setObjects(reg);

   Continuum waterPhase=phase(pc,"water"),airPhase=phase(pc,"air");
   MassConservationErrorReport nativeWater=nativeError("R11_NativeWater_MassConservationError",waterPhase),nativeAir=nativeError("R11_NativeAir_MassConservationError",airPhase);
   Map<String,Object> sourceState=new LinkedHashMap<>();boolean sourceOptionFound=false;
   for(Object source:reg.getConditions().getChildren())if(source.getClass().getSimpleName().equals("MmpUserSourceOption")){
    Object enabled=source.getClass().getMethod("getUserSourceOption").invoke(source);sourceState.put("phase_source_term_enabled",enabled);sourceState.put("source_option_class",source.getClass().getName());sourceOptionFound=true;
    if(!Boolean.FALSE.equals(enabled))throw new IllegalStateException("Unexpected active phase mass source; diagnostic scope requires no source changes");
   }
   if(!sourceOptionFound)throw new IllegalStateException("Phase source option state could not be audited");
   ArrayList<Object> phaseModels=new ArrayList<>();
   for(Continuum phaseObject:List.of(waterPhase,airPhase)){
    ArrayList<String> phaseModelNames=new ArrayList<>();for(Object mod:phaseObject.getModelManager().getChildren())phaseModelNames.add(mod.getClass().getName());
    phaseModels.add(Map.of("phase",phaseObject.getPresentationName(),"models",phaseModelNames));
   }
   sourceState.put("phase_models",phaseModels);sourceState.put("reports",List.of(nativeDefinition(nativeWater),nativeDefinition(nativeAir)));
   sourceState.put("time_discretization",String.valueOf(us.getTimeDiscretizationOption().getSelectedElement()));sourceState.put("dt_s",dt);
   sourceState.put("native_error_units","kg per physical step; divide by dt_s to obtain kg/s");
   sourceState.put("existing_gate_pct_of_inlet",.01);
   sourceState.put("native_comparison_caveat","Native phase report represents transport-equation iteration error. Check agreement with BDF2 density inventory and boundary FaceFlux before interpreting their difference; do not replace one with the other silently.");
   ArrayList<SumReport> phaseWaterFlux=new ArrayList<>(),phaseAirFlux=new ArrayList<>();
   for(Boundary b:reg.getBoundaryManager().getBoundaries()){
    SumReport wr=s.getReportManager().createReport(SumReport.class),ar=s.getReportManager().createReport(SumReport.class);
    wr.setPresentationName("R11_Water_MassFlowRate_"+b.getPresentationName());ar.setPresentationName("R11_Air_MassFlowRate_"+b.getPresentationName());
    wr.setFieldFunction(s.getFieldFunctionManager().getFunction("MassFlowRatewater"));ar.setFieldFunction(s.getFieldFunctionManager().getFunction("MassFlowRateair"));
    for(SumReport pr:List.of(wr,ar)){pr.setRepresentation(fv);pr.setSmooth(false);pr.getParts().setObjects(b);}
    phaseWaterFlux.add(wr);phaseAirFlux.add(ar);
   }
   sourceState.put("phase_flux_fields",List.of("MassFlowRatewater","MassFlowRateair"));sourceState.put("phase_flux_reduction","Unsmoothed boundary-face SumReport; native kg/s values, positive outflow. No multiplication by face area. Native MassFlux[phase] has the opposite sign convention and is not used.");
   Files.writeString(out.resolve("native_phase_report_setup.json"),json(sourceState));
   double previousMass=Double.NaN,secondPreviousMass=Double.NaN;

   long start=System.nanoTime();String status="target_reached";int done=0;
   try(var h=Files.newBufferedWriter(out.resolve("history.csv"));var g=Files.newBufferedWriter(out.resolve("gauges.csv"));var bfout=Files.newBufferedWriter(out.resolve("boundary_flux.csv"));var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"));var nb=Files.newBufferedWriter(out.resolve("native_phase_budget.csv"));var pf=Files.newBufferedWriter(out.resolve("boundary_phase_flux.csv"))){
    h.write("time_s,step,wall_s,max_speed_m_s,max_CFL,interface_CFL,alpha_min,alpha_max,mass_kg,water_volume_m3,net_outward_mass_kg_s,inward_mass_kg_s,vof_substeps\n");
    g.write("time_s,x_m,eta_actual_m,eta_analytic_m\n");bfout.write("time_s,boundary,outward_mass_kg_s\n");av.write("time_s,actual_water_m3,analytic_water_m3\n");
    pf.write("time_s,step,boundary,water_outward_mass_kg_s,air_outward_mass_kg_s,phase_sum_outward_mass_kg_s,faceflux_outward_mass_kg_s\n");
    nb.write("time_s,step,dt_s,native_water_error_kg_step,native_air_error_kg_step,native_sum_error_kg_step,native_water_error_kg_s,native_air_error_kg_s,native_sum_error_kg_s,native_sum_pct_inward_mass,native_abs_sum_pct_inward_mass,bdf2_accumulation_kg_s,faceflux_net_outward_kg_s,bdf2_plus_faceflux_kg_s,bdf2_plus_faceflux_pct_inward_mass,inward_mass_kg_s,phase_net_outward_kg_s,bdf2_plus_phaseflux_kg_s,bdf2_plus_phaseflux_pct_inward_mass,faceflux_minus_phaseflux_kg_s,native_water_error_log,native_air_error_log\n");
    for(int step=0;step<=steps;step++){
     if(step>0){if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL"))){status="stopped_by_marker";break;}s.getSimulationIterator().step(1);done=step;}
     double t=s.getSolution().getPhysicalTime(),v=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),ci=icfl.getReportMonitorValue(),mn=amin.getReportMonitorValue(),mx=amax.getReportMonitorValue(),m=mass.getReportMonitorValue(),w=water.getReportMonitorValue(),net=0,in=0,wall=(System.nanoTime()-start)*1e-9;
     for(int k=0;k<flux.size();k++){double q=flux.get(k).getReportMonitorValue();net+=q;if(q<0)in-=q;bfout.write(t+","+fluxNames.get(k)+","+q+"\n");}bfout.flush();double analyticInventory=analyticWater.getReportMonitorValue();if(Double.isFinite(analyticInventory)){av.write(t+","+w+","+analyticInventory+"\n");av.flush();}else if(step==0){Files.writeString(out.resolve("reference_cache_at_load.json"),json(Map.of("time_s",t,"state","Analytic wave inventory unavailable immediately after checkpoint load; independent physical fields checked before first step","reinitialized",false)));}else throw new IllegalStateException("Analytic wave cache still unavailable after first step");
     if(!Double.isFinite(mn)||!Double.isFinite(mx)||!Double.isFinite(w)||!Double.isFinite(v)||!Double.isFinite(co)||!Double.isFinite(ci)||!Double.isFinite(m)||!Double.isFinite(net)||v>50||mn< -1e-8||mx>1.00000001||Math.abs(t-(initialTime+step*dt))>dt*.1){status="stability_guard";break;}

     double phaseNet=0;
     for(int k=0;k<flux.size();k++){
      double pw=phaseWaterFlux.get(k).getReportMonitorValue(),pa=phaseAirFlux.get(k).getReportMonitorValue();
      if(step>0&&(!Double.isFinite(pw)||!Double.isFinite(pa)))throw new IllegalStateException("Nonfinite native phase boundary mass flow after a guarded step");
      phaseNet+=pw+pa;
      if(step>0)pf.write(t+","+step+","+fluxNames.get(k)+","+pw+","+pa+","+(pw+pa)+","+flux.get(k).getReportMonitorValue()+"\n");
     }pf.flush();
     double nw=nativeWater.getReportMonitorValue(),na=nativeAir.getReportMonitorValue();
     String nwLog=nativeWater.getErrorLog(),naLog=nativeAir.getErrorLog();
     if(step==0){
      Map<String,Object> cache=new LinkedHashMap<>();cache.put("time_s",t);cache.put("water_kg_step",nw);cache.put("air_kg_step",na);cache.put("native_phase_flux_net_kg_s",phaseNet);cache.put("water_error_log",nwLog);cache.put("air_error_log",naLog);cache.put("state","Checkpoint-load report cache only; not accepted as a post-step native transport diagnostic. Both phase reports must be finite after the first guarded step.");
      Files.writeString(out.resolve("native_phase_cache_at_load.json"),json(cache));
     }else{
      if(!Double.isFinite(nw)||!Double.isFinite(na)){Files.writeString(out.resolve("native_phase_error.json"),json(Map.of("time_s",t,"water_error_log",String.valueOf(nwLog),"air_error_log",String.valueOf(naLog))));throw new IllegalStateException("Nonfinite native phase conservation error after a guarded step");}
      double nativeSum=(nw+na)/dt;
      double accumulation=step>=2?(1.5*m-2*previousMass+.5*secondPreviousMass)/dt:Double.NaN;
      double budget=accumulation+net;
      nb.write(t+","+step+","+dt+","+nw+","+na+","+(nw+na)+","+(nw/dt)+","+(na/dt)+","+nativeSum+","+(100*nativeSum/in)+","+(100*(Math.abs(nw)+Math.abs(na))/dt/in)+","+accumulation+","+net+","+budget+","+(100*budget/in)+","+in+","+phaseNet+","+(accumulation+phaseNet)+","+(100*(accumulation+phaseNet)/in)+","+(net-phaseNet)+","+String.valueOf(nwLog).replace(",",";").replace("\n"," ")+","+String.valueOf(naLog).replace(",",";").replace("\n"," ")+"\n");nb.flush();
     }
     secondPreviousMass=previousMass;previousMass=m;
     h.write(t+","+step+","+wall+","+v+","+co+","+ci+","+mn+","+mx+","+m+","+w+","+net+","+in+","+s.getSolverManager().getSolver(SegregatedVofSolver.class).getSubStepCount()+"\n");h.flush();
     if(step==1||step%10==0){for(int k=0;k<xs.length;k++){double a=actual.get(k).getReportMonitorValue()/.02-24,b=analytic.get(k).getReportMonitorValue()/.02-24;if(step==0&&!Double.isFinite(b)&&Double.isFinite(a)&&Math.abs(a)<=1.5){Files.writeString(out.resolve("reference_gauges_at_load.json"),json(Map.of("time_s",t,"state","Analytic plane cache unavailable at load; require finite reference after first guarded step","reinitialized",false)));continue;}if(!Double.isFinite(a)||!Double.isFinite(b)||Math.abs(a)>1.5){Files.writeString(out.resolve("gauge_error.json"),json(Map.of("time_s",t,"x_m",xs[k],"actual_eta_m",a,"analytic_eta_m",b,"actual_error",actual.get(k).getErrorLog(),"analytic_error",analytic.get(k).getErrorLog())));throw new IllegalStateException("Invalid wave gauge at x="+xs[k]+" actual="+a+" analytic="+b);}g.write(t+","+xs[k]+","+a+","+b+"\n");}g.flush();Files.writeString(out.resolve("progress.json"),json(Map.of("time_s",t,"steps",step,"wall_s",wall,"max_speed_m_s",v,"interface_CFL",ci)));}
     if(step>0&&step%250==0)s.saveState(out.resolve(String.format(Locale.ROOT,"checkpoint_t%.3f.sim",t)).toString());
     if(wall>2400){status="wall_budget";break;}
    }
   }
   XyzInternalTable fieldTable=s.getTableManager().createTable(XyzInternalTable.class);fieldTable.getParts().setObjects(reg);fieldTable.setRepresentation(fv);fieldTable.setExtractVertexData(false);
   FieldFunction velocity=s.getFieldFunctionManager().getFunction("Velocity");
   fieldTable.setFieldFunctions(List.of(velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),velocity.getMagnitudeFunction(),alpha,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Density")));fieldTable.extract();fieldTable.export(out.resolve("checkpoint_fields.csv").toString());
   s.saveState(out.resolve("final.sim").toString());Files.writeString(out.resolve("completed.json"),json(Map.of("status",status,"steps",done,"time_s",s.getSolution().getPhysicalTime())));
  }catch(Exception e){try{Files.writeString(out.resolve("macro_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
 }
}