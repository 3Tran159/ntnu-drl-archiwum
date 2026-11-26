package macro;
import star.common.*;import java.nio.file.*;import java.lang.reflect.*;import java.util.*;
public class AuditTransportSettings extends StarMacro{
 public void execute(){
  Simulation s=getActiveSimulation();Map<String,Object> data=new LinkedHashMap<>();
  data.put("physical_time_s",s.getSolution().getPhysicalTime());data.put("solver_steps_taken",0);
  List<Object> objects=new ArrayList<>();objects.addAll(s.getSolverManager().getObjects());
  PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getContinuum("water+air");objects.addAll(pc.getModelManager().getObjects());
  Map<String,Object> result=new LinkedHashMap<>();
  for(Object o:objects){String name=o.toString(),cls=o.getClass().getName();if(!(cls+" "+name).matches("(?i).*(vof|volume.?fraction|implicitunsteady|segregated|flow).*"))continue;
   Map<String,Object> values=new TreeMap<>();values.put("class",cls);values.put("label",name);
   for(Method m:o.getClass().getMethods()){
    if(m.getParameterCount()!=0||!m.getName().startsWith("get")||!m.getName().matches("(?i).*(time|step|cfl|courant|sub|multi|scheme|strategy|discret|implicit|explicit|hric|transport|convection|upwind|order|flux|solution).*"))continue;
    try{values.put(m.getName(),describe(m.invoke(o),2));}catch(Exception e){values.put(m.getName(),"READ_ERROR: "+e.getClass().getSimpleName());}
   }result.put(cls,values);
  }data.put("settings",result);
  try{Files.writeString(Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/transport_settings_audit.json"),json(data));}catch(Exception e){throw new RuntimeException(e);}
 }
 private Object describe(Object o,int depth){
  if(o==null||o instanceof Number||o instanceof Boolean||o instanceof String)return o;
  if(o.getClass().isEnum())return o.toString();
  if(depth==0)return o.toString();
  Map<String,Object> data=new TreeMap<>();data.put("class",o.getClass().getName());data.put("label",o.toString());
  for(Method m:o.getClass().getMethods()){
   if(m.getParameterCount()!=0||!m.getName().matches("get(Value|SIValue|Selected|TargetCfl|TargetCFL|MaxCfl|MaxCFL|NumberOfSubSteps|MaxTimeStep|MinTimeStep|LowerBound|UpperBound|MaxSubSteps|MinSubSteps|MaxSubCycles|SubSteps|SubStepCount|TimeStep|TimeStepSize|MaxIterations|MaximumNumberOfIterations)"))continue;
   try{data.put(m.getName(),describe(m.invoke(o),depth-1));}catch(Exception e){data.put(m.getName(),"READ_ERROR");}
  }return data;
 }
 private String json(Object o){
  if(o==null)return "null";if(o instanceof Number||o instanceof Boolean)return o.toString();
  if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Object a:((Map<?,?>)o).entrySet()){Map.Entry<?,?> e=(Map.Entry<?,?>)a;j.add(json(e.getKey().toString())+":"+json(e.getValue()));}return j.toString();}
  return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
 }
}