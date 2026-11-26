package macro;
import star.common.*;
import star.meshing.*;
import star.base.neo.*;
import star.summary.*;
import java.beans.PropertyDescriptor;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class InspectOnly extends StarMacro {
  private final Path out=Paths.get("F:/ntnu/mesh_screening_20261028/inspection");
  private final List<Map<String,Object>> nodes=new ArrayList<>();
  private final Set<Long> seen=new HashSet<>();
  public void execute() {
    Simulation s=getActiveSimulation();
    try {
      if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("source_copy.sim").toAbsolutePath().normalize()))
        throw new IllegalStateException("Refusing to modify any model except the disposable source copy");
      Files.createDirectories(out);
      Map<String,Object> meta=new LinkedHashMap<>();
      meta.put("session_path",s.getSessionPath());meta.put("version",String.valueOf(s.getStarVersion()));
      meta.put("restore_version",String.valueOf(s.getRestoreVersion()));meta.put("workers",s.getNumberOfWorkers());
      meta.put("iteration",s.getSimulationIterator().getCurrentIteration());meta.put("physical_time",s.getSolution().getPhysicalTime());
      meta.put("auto_save_batch_original",s.getSimulationIterator().getAutoSave().getAutoSaveBatch());
      meta.put("auto_save_enabled_original",s.getSimulationIterator().getAutoSave().getEnabled());
      List<Region> regions=new ArrayList<>();
      for(Object x:s.getRegionManager().getChildren())if(x instanceof Region)regions.add((Region)x);
      List<Map<String,Object>> reps=new ArrayList<>();
      for(Object x:s.getRepresentationManager().getChildren())if(x instanceof FvRepresentation){
        FvRepresentation fv=(FvRepresentation)x;Map<String,Object> r=new LinkedHashMap<>();
        r.put("name",fv.getPresentationName());r.put("cells",fv.getCellCount());reps.add(r);
        if(fv.getCellCount()>0) {
          Object report=fv.generateMeshReport(regions);
          Files.writeString(out.resolve("existing_mesh_report.txt"),String.valueOf(report),StandardCharsets.UTF_8);
        }
      }
      meta.put("volume_representations",reps);
      MeshOperationManager ops=s.get(MeshOperationManager.class);
      snapshot(ops,"mesh_operations",0);
      snapshot(s.getContinuumManager(),"continua",0);
      snapshot(s.getRegionManager(),"regions",0);
      snapshot(s.getGlobalParameterManager(),"global_parameters",0);
      snapshot(s.getSolverManager(),"solvers",0);
      snapshot(s.getGeometryPartManager(),"geometry_parts",0);
      snapshot(s.getReportManager(),"reports",0);
      meta.put("nodes",nodes);
      Files.writeString(out.resolve("model_inventory.json"),json(meta),StandardCharsets.UTF_8);
      s.println("[NTNU] READ_ONLY_INVENTORY_EXPORTED nodes="+nodes.size());
    } catch(Exception ex){throw new RuntimeException(ex);}
  }
  private void snapshot(ClientServerObject o,String path,int depth) {
    if(depth>18||nodes.size()>15000||!seen.add(o.getObjectId()))return;
    Map<String,Object> row=new LinkedHashMap<>();row.put("path",path);row.put("class",o.getClass().getName());row.put("name",o.getPresentationName());
    Map<String,Object> values=new TreeMap<>();row.put("properties",values);nodes.add(row);
    if(o instanceof ScalarPhysicalQuantity) {
      ScalarPhysicalQuantity q=(ScalarPhysicalQuantity)o;
      values.put("si_value",q.getSIValue());values.put("raw_value",q.getRawValue());
      values.put("definition",q.getDefinition());values.put("units",String.valueOf(q.getUnits()));
    }
    List<ClientServerObject> extra=new ArrayList<>();
    for(PropertyDescriptor p:o.getBeanPropertyDescriptors()) {
      Method getter=p.getReadMethod();
      if(getter==null||getter.getParameterCount()!=0)continue;
      String key=p.getName();
      if(key.toLowerCase().matches(".*(icon|font|server|parent|rootobject|simulation|observable|registry|journal).*"))continue;
      try {
        Object v=getter.invoke(o);
        if(v==null||v instanceof Number||v instanceof Boolean||v instanceof String||v instanceof Enum)values.put(key,v);
        else {
          String text=String.valueOf(v);values.put(key,text.length()>2000?text.substring(0,2000)+" [truncated]":text);
          if(v instanceof ClientServerObject && !(v instanceof Units) && key.matches("(?i).*(quantity|size|thickness|stretch|option|value|method|condition|profile|initial).*"))extra.add((ClientServerObject)v);
        }
      } catch(Exception e){values.put(key,"UNAVAILABLE: "+e.getClass().getSimpleName());}
    }
    try {for(Object child:o.getChildren())if(child instanceof ClientServerObject)snapshot((ClientServerObject)child,path+"/"+((ClientServerObject)child).getPresentationName(),depth+1);}
    catch(Exception e){values.put("children_error",e.toString());}
    for(ClientServerObject child:extra)snapshot(child,path+"/@"+child.getPresentationName(),depth+1);
  }
  private static String json(Object o) {
    if(o==null)return "null";
    if(o instanceof Number){double x=((Number)o).doubleValue();return Double.isFinite(x)?o.toString():"null";}
    if(o instanceof Boolean)return o.toString();
    if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Object x:((Map<?,?>)o).entrySet()){Map.Entry<?,?> e=(Map.Entry<?,?>)x;j.add(json(e.getKey().toString())+":"+json(e.getValue()));}return j.toString();}
    if(o instanceof Collection){StringJoiner j=new StringJoiner(",","[","]");for(Object x:(Collection<?>)o)j.add(json(x));return j.toString();}
    String t=o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\r","\\r").replace("\n","\\n").replace("\t","\\t");
    return "\""+t+"\"";
  }
}
