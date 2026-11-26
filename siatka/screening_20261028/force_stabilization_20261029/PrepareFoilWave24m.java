package macro;
import star.common.*;import star.flow.*;import star.vof.*;import star.vis.*;import star.post.*;import star.base.neo.*;import star.base.report.*;
import java.nio.file.*;import java.util.*;
public class PrepareFoilWave24m extends StarMacro {
 private Simulation s;private Path out;private FvRepresentation fv;
 private String json(Object o){if(o==null)return "null";if(o instanceof Number){if(!Double.isFinite(((Number)o).doubleValue()))throw new IllegalStateException("Nonfinite audit value");return o.toString();}if(o instanceof Boolean)return o.toString();if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Iterable<?>)o)j.add(json(x));return j.toString();}return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";}
 private FieldFunction field(String name){for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().equals(name))return f;throw new IllegalStateException("Missing wave field "+name);}
 private void vector(VectorProfile p,FieldFunction f){p.setMethod(FunctionVectorProfileMethod.class);p.getMethod(FunctionVectorProfileMethod.class).setFieldFunction(f);}
 private void scalar(ScalarProfile p,FieldFunction f){p.setMethod(FunctionScalarProfileMethod.class);p.getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
 private void phase(VolumeFractionProfile p,FieldFunction f){p.setMethod(CompositeNMinus1ArrayProfileMethod.class);p.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).setMethod(FunctionScalarProfileMethod.class);p.getMethod(CompositeNMinus1ArrayProfileMethod.class).getProfile(0).getMethod(FunctionScalarProfileMethod.class).setFieldFunction(f);}
 private double extreme(FieldFunction f,NamedObject part,boolean upper){if(upper){MaxReport r=s.getReportManager().createReport(MaxReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(part);return r.getReportMonitorValue();}MinReport r=s.getReportManager().createReport(MinReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(part);return r.getReportMonitorValue();}
 private double surface(FieldFunction f,NamedObject part){SurfaceIntegralReport r=s.getReportManager().createReport(SurfaceIntegralReport.class);r.setFieldFunction(f);r.setRepresentation(fv);r.getParts().setObjects(part);r.setSmooth(false);return r.getReportMonitorValue();}
 public void execute(){s=getActiveSimulation();out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_FOIL_PREP_OUT")));
 try{
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize())||Files.exists(out.resolve("prepared.sim")))throw new IllegalStateException("Fresh disposable input required");
  if(s.getNumberOfGpgpus()!=0||Math.abs(s.getSolution().getPhysicalTime())>1e-10)throw new IllegalStateException("Zero-time CPU preparation only");
  boolean waving=Boolean.parseBoolean(System.getenv("NTNU_FOIL_PREP_WAVE"));
  Region reg=s.getRegionManager().getRegion("fluid");fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");if(fv.getCellCount()!=246885)throw new IllegalStateException("Mesh mismatch");
  s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
  PhysicsContinuum pc=reg.getPhysicsContinuum();if(!pc.getPresentationName().equals("water+air"))throw new IllegalStateException("Continuum mismatch");
  VofWaveModel wm=pc.getModelManager().getModel(VofWaveModel.class);
  FlatVofWave calm=(FlatVofWave)wm.getVofWaveManager().getObject("Calm");
  calm.getPointOnLevel().setComponents(0,0,2);calm.getVerticalDirection().setComponents(0,0,1);calm.getCurrent().setComponents(18,0,0);calm.getWind().setComponents(18,0,0);
  VofWave selected=calm;double period=0;
  if(waving){
   FifthOrderVofWave w=wm.getVofWaveManager().createVofWave(FifthOrderVofWave.class,"NTNU_W01_H05_L20_H24");
   w.getSpecificationOption().setSelected(VofWaveSpecificationOption.Type.WAVE_LENGTH_SPECIFIED);w.getWaterDepth().setValue(24);w.getVofWaveSpecification().getWaveLength().setValue(20);w.getWaveHeight().setValue(.5);w.getPointOnLevel().setComponents(0,0,2);w.getVerticalDirection().setComponents(0,0,1);w.getAdvancingDirection().setComponents(1,0,0);w.getCurrent().setComponents(18,0,0);w.getWind().setComponents(18,0,0);w.getClass().getMethod("setFirstWaveFront",boolean.class).invoke(w,false);
   if(!Boolean.FALSE.equals(w.getClass().getMethod("getFirstWaveFront").invoke(w)))throw new IllegalStateException("First front mismatch");selected=w;period=w.getWavePeriod().getValue();
  }
  wm.setEnableTheoryComparison(true);
  FieldFunction vel=field("Velocity of "+selected.getPresentationName()),pressure=field("Hydrostatic Pressure of Heavy Fluid of "+selected.getPresentationName()),frac=field("Volume Fraction of Heavy Fluid of "+selected.getPresentationName());
  FieldFunction flatP=field("Hydrostatic Pressure of Heavy Fluid of Calm"),flatA=field("Volume Fraction of Heavy Fluid of Calm");
  vector(pc.getInitialConditions().get(VelocityProfile.class),vel);scalar(pc.getInitialConditions().get(InitialPressureProfile.class),pressure);phase(pc.getInitialConditions().get(VolumeFractionProfile.class),frac);
  Boundary inlet=reg.getBoundaryManager().getBoundary("DOMAIN.inlet"),outlet=reg.getBoundaryManager().getBoundary("DOMAIN.outlet"),top=reg.getBoundaryManager().getBoundary("DOMAIN.top"),bed=reg.getBoundaryManager().getBoundary("DOMAIN.bottom"),foil=reg.getBoundaryManager().getBoundary("HF_012_wall");
  inlet.setBoundaryType(InletBoundary.class);inlet.getConditions().get(InletVelocityOption.class).setSelected(InletVelocityOption.Type.COMPONENTS);vector(inlet.getValues().get(VelocityProfile.class),vel);phase(inlet.getValues().get(VolumeFractionProfile.class),frac);
  outlet.setBoundaryType(PressureBoundary.class);top.setBoundaryType(PressureBoundary.class);scalar(outlet.getValues().get(StaticPressureProfile.class),flatP);phase(outlet.getValues().get(VolumeFractionProfile.class),flatA);scalar(top.getValues().get(StaticPressureProfile.class),flatP);phase(top.getValues().get(VolumeFractionProfile.class),flatA);
  BackflowSpecification ob=outlet.getConditions().get(BackflowSpecification.class);ob.getReversedFlowPressureOption().setSelected(ReversedFlowPressureOption.Type.ENVIRONMENTAL);ob.getBackflowVelocityDirectionOption().setSelected(BackflowVelocityDirectionOption.Type.BOUNDARY_NORMAL);ob.getReversedFlowScalarOption().setSelected(ReversedFlowScalarOption.Type.SPECIFIED);
  BackflowSpecification tb=top.getConditions().get(BackflowSpecification.class);tb.getReversedFlowPressureOption().setSelected(ReversedFlowPressureOption.Type.STATIC);tb.getBackflowVelocityDirectionOption().setSelected(BackflowVelocityDirectionOption.Type.EXTRAPOLATED);tb.getReversedFlowScalarOption().setSelected(ReversedFlowScalarOption.Type.SPECIFIED);
  bed.setBoundaryType(WallBoundary.class);bed.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.SLIP);
  foil.setBoundaryType(WallBoundary.class);foil.getConditions().get(WallShearStressOption.class).setSelected(WallShearStressOption.Type.NO_SLIP);
  for(String n:new String[]{"Q2D_span_source","Q2D_span_target"})reg.getBoundaryManager().getBoundary(n).setBoundaryType(SymmetryBoundary.class);
  reg.getConditions().get(VofWaveZoneOption.class).setSelected(VofWaveZoneOptionEnum.FORCING_DAMPING);reg.getConditions().get(ForcingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);reg.getConditions().get(DampingLengthSpecificationOption.class).setSelected(LengthSpecificationOptionEnum.BOUNDARY);reg.getValues().get(ForcingVofWaveSpecification.class).setForcingVofWave(selected);
  for(Boundary b:reg.getBoundaryManager().getBoundaries()){b.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(VofWaveForcingBoundaryOption.NO);b.getConditions().get(VofWaveDampingBoundaryOption.class).setSelected(VofWaveDampingBoundaryOption.NO);}
  inlet.getConditions().get(VofWaveForcingBoundaryOption.class).setSelected(VofWaveForcingBoundaryOption.YES);outlet.getConditions().get(VofWaveDampingBoundaryOption.class).setSelected(VofWaveDampingBoundaryOption.YES);
  inlet.getValues().get(VofWaveForcingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(20);outlet.getValues().get(VofWaveDampingLength.class).getMethod(ConstantScalarProfileMethod.class).setConstant(20);
  for(Object x:s.getSolverStoppingCriterionManager().getChildren()){
   if(x instanceof PhysicalTimeStoppingCriterion||x instanceof StepStoppingCriterion)((SolverStoppingCriterion)x).setIsUsed(false);
   if(x instanceof InnerIterationStoppingCriterion){((InnerIterationStoppingCriterion)x).setMaximumNumberInnerIterations(10);((SolverStoppingCriterion)x).setIsUsed(true);}
  }
  ImplicitUnsteadySolver us=s.getSolverManager().getSolver(ImplicitUnsteadySolver.class);us.getTimeStep().setValue(.001);us.getTimeDiscretizationOption().setSelected(TimeDiscretizationOption.Type.SECOND_ORDER);
  s.getSolution().clearSolutionWithoutMeshReset();s.getSolution().initializeSolution();
  if(Math.abs(s.getSolution().getPhysicalTime())>1e-12)throw new IllegalStateException("Preparation advanced time");
  UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setFunctionName("FoilPrepUnit");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDefinition("1");
  ArrayList<Object> ba=new ArrayList<>();FieldFunction pos=s.getFieldFunctionManager().getFunction("Position");double spanArea=47.997684231819/.02;
  for(Boundary b:reg.getBoundaryManager().getBoundaries()){
   String n=b.getPresentationName();double area=surface(one,b),expected;
   if(n.equals("HF_012_wall"))expected=2.420247199693753*.02;else if(n.startsWith("Q2D_span_"))expected=spanArea;else if(n.endsWith("inlet")||n.endsWith("outlet"))expected=.6;else if(n.endsWith("top")||n.endsWith("bottom"))expected=1.6;else throw new IllegalStateException("Unexpected boundary "+n);
   if(!Double.isFinite(area)||Math.abs(area-expected)>expected*1e-6)throw new IllegalStateException("Boundary area mismatch "+n+" "+area);
   Map<String,Object> v=new LinkedHashMap<>();v.put("name",n);v.put("type",b.getBoundaryType().getClass().getSimpleName());v.put("area_m2",area);
   if(n.endsWith("inlet")||n.endsWith("outlet")){double plane=n.endsWith("inlet")?-35:45;double lo=extreme(pos.getComponentFunction(0),b,false),hi=extreme(pos.getComponentFunction(0),b,true);if(Math.max(Math.abs(lo-plane),Math.abs(hi-plane))>1e-8)throw new IllegalStateException("X boundary plane mismatch");v.put("x_m",plane);}
   if(n.endsWith("top")||n.endsWith("bottom")){double plane=n.endsWith("top")?8:-22;double lo=extreme(pos.getComponentFunction(2),b,false),hi=extreme(pos.getComponentFunction(2),b,true);if(Math.max(Math.abs(lo-plane),Math.abs(hi-plane))>1e-8)throw new IllegalStateException("Z boundary plane mismatch");v.put("z_m",plane);}
   ba.add(v);
  }
  ArrayList<Object> gauges=new ArrayList<>();FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
  for(double x:new double[]{-10,-5,2.5,5,10,15,20}){
   PlaneSection q=s.getPartManager().createPlaneSection();q.getInputParts().setObjects(reg);q.setOrigin(new DoubleVector(new double[]{x,.02,2}));q.setOrientation(new DoubleVector(new double[]{1,0,0}));
   double planeHeight=surface(one,q)/.02,a=surface(alpha,q)/.02-24,b=surface(frac,q)/.02-24;
   if(Math.abs(planeHeight-30)>1e-5||!Double.isFinite(a)||Math.abs(a)>1.5)throw new IllegalStateException("Initial gauge mismatch");
   gauges.add(Map.of("x_m",x,"height_m",planeHeight,"eta_actual_m",a,"eta_analytic_m",b));
  }
  double minA=extreme(alpha,reg,false),maxA=extreme(alpha,reg,true),maxV=extreme(s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction(),reg,true);
  if(minA< -1e-8||maxA>1.00000001||!Double.isFinite(maxV)||maxV>50)throw new IllegalStateException("Initial field guard");
  Map<String,Object> audit=new LinkedHashMap<>();audit.put("status","prepared_zero_steps");audit.put("time_s",s.getSolution().getPhysicalTime());audit.put("flow_steps",0);audit.put("cells",fv.getCellCount());audit.put("gpu",false);audit.put("wave",waving);audit.put("wave_class",selected.getClass().getSimpleName());audit.put("wave_name",selected.getPresentationName());audit.put("wave_period_s",period);audit.put("boundaries",ba);audit.put("gauges",gauges);audit.put("initial_alpha_min",minA);audit.put("initial_alpha_max",maxA);audit.put("initial_max_speed_m_s",maxV);
  audit.put("settings",Map.of("order","SECOND_ORDER","dt_s",.001,"inner",10,"water_depth_m",24,"waterline_z_m",2,"U_m_s",18,"submergence_m",2,"outlet_pressure","ENVIRONMENTAL","bottom","SLIP","top","STATIC","forcing_m",20,"damping_m",20));
  audit.put("bindings",Map.of("initial_velocity",vel.getFunctionName(),"initial_pressure",pressure.getFunctionName(),"initial_phase",frac.getFunctionName(),"outlet_pressure",flatP.getFunctionName(),"outlet_phase",flatA.getFunctionName(),"forcing_wave",selected.getPresentationName()));
  audit.put("scope","Matched calm/wave input preparation only; neither startup nor wave-grid/time/propagation accuracy established");
  s.saveState(out.resolve("prepared.sim").toString());Files.writeString(out.resolve("initial_audit.json"),json(audit));
 }catch(Exception ex){try{Files.writeString(out.resolve("prep_error.txt"),ex.toString());}catch(Exception ignored){}throw new RuntimeException(ex);}
 }
}
