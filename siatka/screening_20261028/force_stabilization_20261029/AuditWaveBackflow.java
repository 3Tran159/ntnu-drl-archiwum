package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.flow.*;import star.vof.*;import star.post.*;
import java.nio.file.*;import java.util.*;
public class AuditWaveBackflow extends StarMacro {
 private static String json(Object o){
  if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(var e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}
  if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)o)j.add(json(x));return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
 private static Object inspect(Object o,int depth){
  if(o==null||o instanceof Number||o instanceof String||o instanceof Boolean||o instanceof Enum)return o;
  if(depth<=0)return o.toString();
  if(o instanceof Collection){ArrayList<Object> a=new ArrayList<>();for(Object x:(Collection<?>)o)a.add(inspect(x,depth-1));return a;}
  Map<String,Object> d=new LinkedHashMap<>();d.put("class",o.getClass().getName());
  String allowed="getPresentationName|getSelected|getMethod|getFieldFunction|getFunctionName|getConstant|getQuantity|getValue|getSIValue|getRawVector|getComponents|getProfiles|getObjects|getForcingVofWave|getWaveForcingLength|getWaveDampingLength|getSelectedElement|getReversedFlowPressureOption|getBackflowVelocityDirectionOption|getReversedFlowScalarOption";
  for(java.lang.reflect.Method m:o.getClass().getMethods())if(m.getParameterCount()==0&&m.getName().matches(allowed)){
   try{d.put(m.getName(),inspect(m.invoke(o),depth-1));}catch(Exception ex){d.put(m.getName(),"READ_ERROR");}
  }
  return d;
 }
 public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_WAVE_AUDIT_OUT")));
  try{
   if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable input copy required");
   if(s.getNumberOfGpgpus()!=0)throw new IllegalStateException("Read-only CPU audit only");
   double before=s.getSolution().getPhysicalTime();if(before<=0)throw new IllegalStateException("Transient checkpoint required");
   Region fluid=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
   if(fv.getCellCount()!=53200)throw new IllegalStateException("Unexpected mesh");
   s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   FieldFunction vel=s.getFieldFunctionManager().getFunction("Velocity"),alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater");
   XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(fluid);table.setRepresentation(fv);table.setExtractVertexData(false);
   table.setFieldFunctions(List.of(vel.getComponentFunction(0),vel.getComponentFunction(1),vel.getComponentFunction(2),vel.getMagnitudeFunction(),alpha,s.getFieldFunctionManager().getFunction("Pressure"),s.getFieldFunctionManager().getFunction("CourantNumber"),s.getFieldFunctionManager().getFunction("Density")));
   table.extract();table.export(out.resolve("checkpoint_fields.csv").toString());
   ArrayList<Map<String,Object>> bc=new ArrayList<>();
   for(Boundary b:fluid.getBoundaryManager().getBoundaries()){
    MassFlowReport mass=s.getReportManager().createReport(MassFlowReport.class);mass.getParts().setObjects(b);mass.setRepresentation(fv);
    Map<String,Object> item=new LinkedHashMap<>();item.put("name",b.getPresentationName());item.put("type",b.getBoundaryType().getClass().getSimpleName());item.put("mass_outward_kg_s",mass.getReportMonitorValue());
    ArrayList<Object> values=new ArrayList<>(),conditions=new ArrayList<>();
    for(Object v:b.getValues().getChildren())if(v.getClass().getSimpleName().matches(".*(Velocity|VolumeFraction|Pressure|Wave|Backflow|FlowDirection|Turbulence).*"))values.add(inspect(v,4));
    for(Object v:b.getConditions().getChildren())if(v.getClass().getSimpleName().matches(".*(Wave|Backflow|FlowDirection).*"))conditions.add(inspect(v,3));
    if(b.getBoundaryType() instanceof PressureBoundary){
     BackflowSpecification back=b.getConditions().get(BackflowSpecification.class);
     item.put("backflow_pressure",String.valueOf(back.getReversedFlowPressureOption().getSelectedElement()));
     item.put("backflow_direction",String.valueOf(back.getBackflowVelocityDirectionOption().getSelectedElement()));
     item.put("backflow_scalar",String.valueOf(back.getReversedFlowScalarOption().getSelectedElement()));
    }
    item.put("values",values);item.put("conditions",conditions);bc.add(item);
   }
   ArrayList<Object> regionWave=new ArrayList<>();
   for(Object v:fluid.getValues().getChildren())if(v.getClass().getSimpleName().matches(".*(Wave|Damping|Forcing).*"))regionWave.add(inspect(v,4));
   for(Object v:fluid.getConditions().getChildren())if(v.getClass().getSimpleName().matches(".*(Wave|Damping|Forcing).*"))regionWave.add(inspect(v,3));
   Files.writeString(out.resolve("wave_boundary_bindings.json"),json(Map.of("time_s",before,"boundaries",bc,"region_wave",regionWave)));
   double after=s.getSolution().getPhysicalTime();if(Math.abs(after-before)>1e-12)throw new IllegalStateException("Audit advanced time");
   Files.writeString(out.resolve("audit.json"),json(Map.of("time_s",before,"steps_taken",0,"cells",fv.getCellCount(),"gpu_count",s.getNumberOfGpgpus(),"boundaries",bc,"status","fields_exported_zero_steps","scope","Spatial diagnostic of saved no-foil wave state; not wave acceptance")));
  }catch(Exception ex){try{Files.writeString(out.resolve("audit_error.txt"),ex.toString());}catch(Exception ignored){}throw new RuntimeException(ex);}
 }
}
