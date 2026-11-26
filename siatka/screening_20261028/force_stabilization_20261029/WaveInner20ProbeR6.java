package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.post.*;
import java.nio.file.*;import java.util.*;
public class WaveInner20ProbeR6 extends StarMacro {
 private Simulation s;private Path out;private Region reg;private FvRepresentation fv;
 private String json(Object o){
  if(o==null)return "null";if(o instanceof Number||o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Map.Entry<?,?> e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
  if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Iterable<?>)o)j.add(json(a));return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
 private MaxReport max(String name,FieldFunction ff,NamedObject part){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setPresentationName(name);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(part);r.createMonitor();return r;}
 private SurfaceIntegralReport integral(PlaneSection p,FieldFunction ff){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(ff);r.setRepresentation(fv);r.getParts().setObjects(p);r.setSmooth(false);return r;}
 public void execute(){s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_OUT")));
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable input copy required");
   if(Files.exists(out.resolve("history.csv")))throw new IllegalStateException("Attempt already used");
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("Exactly one GPU required");
   double dt=Double.parseDouble(System.getenv("NTNU_WAVE_DT"));int steps=Integer.parseInt(System.getenv("NTNU_WAVE_STEPS"));
   if(dt<.0005||dt>.001||steps<50||steps>3000)throw new IllegalStateException("Unsupported pilot length or step");
   reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()!=Long.parseLong(System.getenv("NTNU_WAVE_CELLS"))||Math.abs(s.getSolution().getPhysicalTime()-.5)>1e-8)throw new IllegalStateException("Input state mismatch");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
   for(Object x:s.getSolverStoppingCriterionManager().getChildren()){
    if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
    if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(20);((SolverStoppingCriterion)x).setIsUsed(true);}
   }
   ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);us.getTimeStep().setValue(dt);us.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
   PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");
   FifthOrderVofWave wave=(FifthOrderVofWave)reg.getValues().get(ForcingVofWaveSpecification.class).getForcingVofWave();
   if(!Boolean.FALSE.equals(wave.getClass().getMethod("getFirstWaveFront").invoke(wave))||Math.abs(wave.getWaterDepth().getValue()-24)>1e-8)throw new IllegalStateException("Wave scope mismatch");
   double initialTime=s.getSolution().getPhysicalTime();
   Boundary outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet"),bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom");
   if(!String.valueOf(outlet.getConditions().get(BackflowSpecification.class).getReversedFlowPressureOption().getSelectedElement()).equals("ENVIRONMENTAL")||!String.valueOf(bed.getConditions().get(WallShearStressOption.class).getSelectedElement()).equals("SLIP"))throw new IllegalStateException("Checkpoint boundary settings mismatch");
   Files.writeString(out.resolve("continuation_identity.json"),json(Map.of("initial_time_s",initialTime,"target_time_s",.75,"reinitialized",false,"outlet_backflow","ENVIRONMENTAL","bottom","SLIP","scope","Matched short diagnostic of the0.618s mass-budget spike; only inneriterations10to20 changed; not propagation acceptance")));
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
   Files.writeString(out.resolve("setup.json"),json(Map.of("cells",fv.getCellCount(),"dt_s",dt,"inner",20,"order","SECOND_ORDER","wave_period_s",wave.getWavePeriod().getValue(),"steps",steps,"gpu_count",s.getNumberOfGpgpus(),"scope","No-foil short propagation pilot; not force or final propagation validation")));
   VolumeIntegralReport analyticWater=s.getReportManager().createReport(VolumeIntegralReport.class);analyticWater.setRepresentation(fv);analyticWater.setFieldFunction(theory);analyticWater.getParts().setObjects(reg);
   long start=System.nanoTime();String status="target_reached";int done=0;
   try(var h=Files.newBufferedWriter(out.resolve("history.csv"));var g=Files.newBufferedWriter(out.resolve("gauges.csv"));var bfout=Files.newBufferedWriter(out.resolve("boundary_flux.csv"));var av=Files.newBufferedWriter(out.resolve("analytic_inventory.csv"))){
    h.write("time_s,step,wall_s,max_speed_m_s,max_CFL,interface_CFL,alpha_min,alpha_max,mass_kg,water_volume_m3,net_outward_mass_kg_s,inward_mass_kg_s,vof_substeps\n");
    g.write("time_s,x_m,eta_actual_m,eta_analytic_m\n");bfout.write("time_s,boundary,outward_mass_kg_s\n");av.write("time_s,actual_water_m3,analytic_water_m3\n");
    for(int step=0;step<=steps;step++){
     if(step>0){if(Files.exists(out.resolve("STOP"))||Files.exists(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/STOP_ALL"))){status="stopped_by_marker";break;}s.getSimulationIterator().step(1);done=step;}
     double t=s.getSolution().getPhysicalTime(),v=vmax.getReportMonitorValue(),co=cfl.getReportMonitorValue(),ci=icfl.getReportMonitorValue(),mn=amin.getReportMonitorValue(),mx=amax.getReportMonitorValue(),m=mass.getReportMonitorValue(),w=water.getReportMonitorValue(),net=0,in=0,wall=(System.nanoTime()-start)*1e-9;
     for(int k=0;k<flux.size();k++){double q=flux.get(k).getReportMonitorValue();net+=q;if(q<0)in-=q;bfout.write(t+","+fluxNames.get(k)+","+q+"\n");}bfout.flush();double analyticInventory=analyticWater.getReportMonitorValue();if(Double.isFinite(analyticInventory)){av.write(t+","+w+","+analyticInventory+"\n");av.flush();}else if(step==0){Files.writeString(out.resolve("reference_cache_at_load.json"),json(Map.of("time_s",t,"state","Analytic wave inventory unavailable immediately after checkpoint load; independent physical fields checked before first step","reinitialized",false)));}else throw new IllegalStateException("Analytic wave cache still unavailable after first step");
     if(!Double.isFinite(v)||!Double.isFinite(co)||!Double.isFinite(ci)||!Double.isFinite(m)||!Double.isFinite(net)||v>50||mn< -1e-8||mx>1.00000001||Math.abs(t-(initialTime+step*dt))>dt*.1){status="stability_guard";break;}
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
