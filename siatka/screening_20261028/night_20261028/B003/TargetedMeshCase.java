package macro;
import star.common.*;
import star.meshing.*;
import star.prismmesher.*;
import star.base.neo.*;
import star.base.report.*;
import star.vis.*;
import java.beans.PropertyDescriptor;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.security.MessageDigest;
import java.math.BigDecimal;
import javax.json.Json;
import javax.json.JsonObject;

/** Model-specific, mesh-only pilot for the inspected HF_mesh_v5, 21.02.007 R8. */
public class TargetedMeshCase extends StarMacro {
  private final List<Map<String,Object>> nodes=new ArrayList<>();
  private final Set<Long> seen=new HashSet<>();
  private static final String TARGET="mesh_operations/Automated Mesh/Custom Controls/HF_surface/Values/Target Surface Size";
  private Path out; private Simulation s;
  private final List<String> notes=new ArrayList<>();
  public void execute() {
    s=getActiveSimulation();
    try {
      Path input=Paths.get(Objects.requireNonNull(System.getenv("NTNU_MESH_JOB"),"Missing NTNU_MESH_JOB")).toAbsolutePath();
      JsonObject job; try(var reader=Json.createReader(Files.newBufferedReader(input))){job=reader.readObject();}
      out=input.getParent();
      require(Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("baseline_copy.sim")),"Wrong working copy");
      require(s.getStarVersion().toString().contains("21.02.007")&&s.getStarVersion().toString().contains("r8"),"Wrong build/precision");
      require(job.getInt("schema_version")==1,"Wrong job schema");
      require(sha(Files.readAllBytes(out.resolve("baseline_copy.sim"))).equals(job.getString("baseline_sha256")),"Baseline copy mismatch");
      require(s.getSimulationIterator().getCurrentIteration()==0,"Clean baseline still contains solver iterations");
      for(Object x:s.getRepresentationManager().getChildren())if(x instanceof FvRepresentation)
        require(((FvRepresentation)x).getCellCount()==0,"Clean baseline still contains volume cells");
      String expected=job.getString("locked_settings_sha256");
      String pre=frozen(); Files.writeString(out.resolve("locked_before.json"),pre);
      require(sha(pre.getBytes(StandardCharsets.UTF_8)).equals(expected),"Frozen baseline mismatch; inspect locked_before.json");
      JsonObject params=job.getJsonObject("parameters_m");
      require(params.size()==4&&params.containsKey("foil_target_m")&&params.containsKey("curve_target_m")&&params.containsKey("enhanced_prisms")&&params.containsKey("core_aspect_ratio"),"Unsupported parameter binding");
      double target=params.getJsonNumber("foil_target_m").doubleValue();
      require(Math.abs(target-0.0064)<1e-12,"Keep foil target fixed");
      double curveTarget=params.getJsonNumber("curve_target_m").doubleValue();
      double aspect=params.getJsonNumber("core_aspect_ratio").doubleValue();
      boolean enhanced=params.getBoolean("enhanced_prisms");
      require((curveTarget==0.0032||curveTarget==0.0064)&&(aspect==1.0||aspect==2.0||aspect==4.0),"Outside targeted diagnostic bounds");
      require(!enhanced||aspect==1.0,"Enhanced algorithm has its own aspect control; no ineffective aspect variation");
      AutoMeshOperation op=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Automated Mesh");
      SurfaceCustomMeshControl control=(SurfaceCustomMeshControl)op.getCustomMeshControls().getObject("HF_surface");
      require(control.getEnableControl(),"Foil control disabled");
      PartsTargetSurfaceSize size=control.getCustomValues().get(PartsTargetSurfaceSize.class);
      double base=op.getDefaultValues().get(BaseSize.class).getSIValue();
      require(Math.abs(base-0.8192)<1e-12,"Base size changed");
      size.setRelativeSize(target/base*100.0);
      CurveCustomMeshControl edge=(CurveCustomMeshControl)op.getCustomMeshControls().getObject("Curve Control");
      edge.getCustomValues().get(PartsTargetSurfaceSize.class).getAbsoluteSize().getValue().setValue(curveTarget);
      op.getDefaultValues().get(PrismLayerCoreLayerAspectRatio.class).setValue(aspect);
      ((PrismAutoMesher)op.getMeshers().getObject("Prism Layer Mesher")).setEnhancedPrismLayers(enhanced);
      Map<String,Object> before=readback(size,base,expected,"locked_applied.json");
      if("1".equals(System.getenv("NTNU_MESH_PROBE"))){
        Files.writeString(out.resolve("PROBE_OK.txt"),"Clean-copy identity, fixed settings and target readback verified; no mesh generated.");
        s.println("[NTNU] PROBE_OK");return;
      }
      int iteration=s.getSimulationIterator().getCurrentIteration();
      long tick=System.nanoTime();
      s.println("[NTNU] MESH_START "+job.getString("case_id")+" foil_target_m="+target);
      s.getMeshPipelineController().generateVolumeMesh();
      double elapsed=(System.nanoTime()-tick)*1e-9;
      FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
      long cells=fv.getCellCount();require(cells>0,"No generated cells");
      require(s.getSimulationIterator().getCurrentIteration()==iteration,"Unexpected solver iteration");
      Map<String,Object> after=readback(size,base,expected,"locked_after.json");
      Region region=s.getRegionManager().getRegion("fluid");
      Map<String,Object> metrics=new LinkedHashMap<>();metrics.put("cell_count",cells);metrics.put("mesh_time_s",elapsed);
      NeoProperty meshReport=fv.generateMeshReport(List.of(region));
      Files.writeString(out.resolve("mesh_report_properties.txt"),meshReport.toFormattedString());
      for(String key:List.of("NegativeVolumeCells","UnclosedCells","DegeneratedFeCells")){
        Object value=meshReport.get(key);if(value instanceof Number)metrics.put(key,((Number)value).longValue());
      }
      // Sum of diagnostic occurrences, not a deduplicated count: zero certifies all three checks are zero.
      if(metrics.keySet().containsAll(List.of("NegativeVolumeCells","UnclosedCells","DegeneratedFeCells")))
        metrics.put("invalid_cells",((Number)metrics.get("NegativeVolumeCells")).longValue()+((Number)metrics.get("UnclosedCells")).longValue()+((Number)metrics.get("DegeneratedFeCells")).longValue());
      List<String> fields=new ArrayList<>();for(FieldFunction f:s.getFieldFunctionManager().getScalarFieldFunctions())fields.add(f.getFunctionName()+" | "+f.getPresentationName());
      Collections.sort(fields);Files.write(out.resolve("available_scalar_fields.txt"),fields);
      scalar(metrics,"min_cell_volume_m3",new String[]{"Volume","CellVolume"},false,region,fv);
      scalar(metrics,"min_cell_quality",new String[]{"CellQuality"},false,region,fv);
      scalar(metrics,"min_face_validity",new String[]{"FaceValidity"},false,region,fv);
      scalar(metrics,"min_volume_change",new String[]{"VolumeChange"},false,region,fv);
      scalar(metrics,"max_skewness_angle_deg",new String[]{"SkewnessAngle"},true,region,fv);
      diagnostics(metrics,"CellQuality",0.01,false,region,fv);
      diagnostics(metrics,"SkewnessAngle",80.0,true,region,fv);
      diagnostics(metrics,"SkewnessAngle",85.0,true,region,fv);
      diagnostics(metrics,"VolumeChange",0.01,false,region,fv);
      diagnostics(metrics,"FaceValidity",0.95,false,region,fv);
      prismAudit(metrics,region,fv);
      Path save=Paths.get(job.getString("save_sim_path")).toAbsolutePath();require(save.getParent().equals(out),"Unsafe save path");
      s.saveState(save.toString());
      Map<String,Object> result=new LinkedHashMap<>();
      result.put("schema_version",1);for(String key:List.of("case_id","run_id","baseline_sha256"))result.put(key,job.getString(key));
      result.put("evidence_kind","measured");result.put("solver_version","21.02.007");result.put("precision","double");
      result.put("generation_status","completed");result.put("solver_iterations_executed",0);
      result.put("readback_before_mesh",before);result.put("readback_after_mesh",after);result.put("metrics",metrics);
      result.put("reviews",Map.of("prism_review",Map.of("status","pending","evidence","Saved mesh and mesher log require coverage/transition inspection"),"local_resolution_review",Map.of("status","pending","evidence","Threshold tables are diagnostic only; hydrodynamic resolution not verified")));
      result.put("saved_model_path",save.toString());result.put("save_status","completed");result.put("notes",notes);
      Path dest=Paths.get(job.getString("result_path")).toAbsolutePath();require(dest.getParent().equals(out),"Unsafe result path");
      Path temp=out.resolve("measurement.tmp");Files.writeString(temp,json(result));Files.move(temp,dest,StandardCopyOption.REPLACE_EXISTING);
      s.println("[NTNU] MESH_CASE_COMPLETED cells="+cells+" seconds="+elapsed);
    } catch(Exception e){throw new RuntimeException(e);}
  }
  private Map<String,Object> readback(PartsTargetSurfaceSize size,double base,String expected,String file)throws Exception{
    String value=frozen();Files.writeString(out.resolve(file),value);String hash=sha(value.getBytes(StandardCharsets.UTF_8));
    require(hash.equals(expected),"Locked setting changed: "+file);
    return Map.of("parameters_m",appliedParameters(size,base),"locked_settings_sha256",hash);
  }
  private void scalar(Map<String,Object> metrics,String key,String[] names,boolean maximum,NamedObject reg,FvRepresentation fv){
    try{
      FieldFunction f=null;for(String name:names)if(s.getFieldFunctionManager().hasFunction(name)){f=s.getFieldFunctionManager().getFunction(name);break;}
      if(f==null){notes.add("Unavailable field for "+key);return;}
      ScalarReport report=maximum?s.getReportManager().createReport(MaxReport.class):s.getReportManager().createReport(MinReport.class);
      report.setPresentationName("NTNU_"+key);report.setFieldFunction(f);report.getParts().setObjects(reg);report.setRepresentation(fv);
      double value=report.monitoredValue();String errors=report.getErrorLog();
      report.printReport(out.resolve(key+".txt").toString(),false);
      if(!Double.isFinite(value)||!errors.isBlank()){notes.add(key+" report error: "+errors);return;}
      // STAR 21.02 SkewnessAngle is dimensionless, with numerical values already in degrees.
      metrics.put(key,value);notes.add(key+" field="+f.getFunctionName()+" population="+reg.getPresentationName()+" units="+report.getUnits());
    }catch(Exception e){notes.add(key+" unavailable: "+e);}
  }
  private void prismAudit(Map<String,Object> metrics,Region region,FvRepresentation fv){
    try{
      Boundary foil=(Boundary)region.getBoundaryManager().getObject("HF_v2 2.ColoredFace1");
      scalar(metrics,"min_foil_prism_layers",new String[]{"PrismLayerNumber"},false,foil,fv);
      scalar(metrics,"max_foil_prism_layers",new String[]{"PrismLayerNumber"},true,foil,fv);
      scalar(metrics,"min_foil_prism_total_thickness_m",new String[]{"PrismCellThickness"},false,foil,fv);
      scalar(metrics,"max_foil_prism_total_thickness_m",new String[]{"PrismCellThickness"},true,foil,fv);
      for(String mode:List.of("any","full_15")){
        UserFieldFunction mask=s.getFieldFunctionManager().createFieldFunction();mask.setPresentationName("NTNU_coverage_"+mode);mask.setFunctionName("NTNU_coverage_"+mode);
        mask.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);
        mask.setDefinition("${PrismLayerNumber} >= "+(mode.equals("any")?"0.5":"14.5")+" ? 1.0 : 0.0");
        AreaAverageReport area=s.getReportManager().createReport(AreaAverageReport.class);area.setPresentationName("NTNU_foil_area_coverage_"+mode);
        area.setFieldFunction(mask);area.setRepresentation(fv);area.getParts().setObjects(foil);
        double fraction=area.monitoredValue();area.printReport(out.resolve("foil_coverage_"+mode+".txt").toString(),false);
        if(!Double.isFinite(fraction)||!area.getErrorLog().isBlank())throw new IllegalStateException(area.getErrorLog());
        metrics.put("foil_area_fraction_"+mode+"_prism_layers",fraction);
      }
      FieldFunction layer=s.getFieldFunctionManager().getFunction("PrismLayerNumber");
      ThresholdPart first=s.getPartManager().createThresholdPart();first.setPresentationName("NTNU_first_prism_layer");
      first.getInputParts().setObjects(region);first.setFieldFunction(layer);first.setRange(new DoubleVector(new double[]{0.5,1.5}));first.setMode(ThresholdMode.BETWEEN_TAG);
      scalar(metrics,"min_first_prism_cell_thickness_m",new String[]{"PrismCellThickness"},false,first,fv);
      scalar(metrics,"max_first_prism_cell_thickness_m",new String[]{"PrismCellThickness"},true,first,fv);
      diagnostics(metrics,"PrismLayerNumber",14.5,false,foil,fv);
      notes.add("Prism layer-number and thickness fields are STAR geometry diagnostics; coverage is foil-area-weighted, not achieved y-plus.");
    }catch(Exception e){notes.add("Prism diagnostics incomplete: "+e);}
  }
  private void diagnostics(Map<String,Object> metrics,String name,double cutoff,boolean above,NamedObject reg,FvRepresentation fv){
    try{
      if(!s.getFieldFunctionManager().hasFunction(name))return;
      FieldFunction f=s.getFieldFunctionManager().getFunction(name);
      ThresholdPart part=s.getPartManager().createThresholdPart();part.setPresentationName("NTNU_diagnostic_"+name);
      part.getInputParts().setObjects(reg);part.setFieldFunction(f);part.setRange(new DoubleVector(new double[]{cutoff,cutoff}));
      part.setMode(above?ThresholdMode.ABOVE_TAG:ThresholdMode.BELOW_TAG);
      ElementCountReport report=s.getReportManager().createReport(ElementCountReport.class);report.setPresentationName("NTNU_count_"+name);
      report.setRepresentation(fv);report.getParts().setObjects(part);double count=report.getReportMonitorValue();
      if(!report.getErrorLog().isBlank()||!Double.isFinite(count))throw new IllegalStateException(report.getErrorLog());
      metrics.put("diagnostic_"+name+(above?"_above_":"_below_")+cutoff,count);
      if(count>0&&count<=100000){
        XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.setPresentationName("NTNU_cells_"+name);
        table.getParts().setObjects(part);table.setFieldFunctions(List.of(f));table.setRepresentation(fv);table.setExtractVertexData(false);
        table.extract();table.export(out.resolve("diagnostic_"+name+".csv").toString());
      }
      notes.add("Diagnostic "+name+" < "+cutoff+": "+count+" elements in "+reg.getPresentationName()+"; review trigger, not universal acceptance limit");
    }catch(Exception e){notes.add("Local diagnostic "+name+" unavailable: "+e);}
  }
  private Map<String,Object> appliedParameters(PartsTargetSurfaceSize size,double base){
    AutoMeshOperation op=(AutoMeshOperation)s.get(MeshOperationManager.class).getObject("Automated Mesh");
    CurveCustomMeshControl edge=(CurveCustomMeshControl)op.getCustomMeshControls().getObject("Curve Control");
    boolean enhanced=((PrismAutoMesher)op.getMeshers().getObject("Prism Layer Mesher")).getEnhancedPrismLayers();
    Map<String,Object> p=new LinkedHashMap<>();p.put("foil_target_m",base*size.getRelativeSizeScalar().getRawValue()/100.0);p.put("curve_target_m",edge.getCustomValues().get(PartsTargetSurfaceSize.class).getAbsoluteSize().getValue().getSIValue());p.put("enhanced_prisms",enhanced);
    p.put("core_aspect_ratio",enhanced?1.0:op.getDefaultValues().get(PrismLayerCoreLayerAspectRatio.class).getSIValue());return p;
  }
  private String frozen(){
    nodes.clear();seen.clear();snapshot(s.get(MeshOperationManager.class),"mesh_operations",0);
    snapshot(s.getContinuumManager(),"continua",0);snapshot(s.getRegionManager(),"regions",0);
    snapshot(s.getGlobalParameterManager(),"global_parameters",0);snapshot(s.getSolverManager(),"solvers",0);snapshot(s.getGeometryPartManager(),"geometry_parts",0);
    Set<String> skip=Set.of("si_value","raw_value","definition","units","CurrentIterationCount","PhysicalTime","TriangleCount","DescriptionsOutput");
    Map<String,String> flat=new TreeMap<>();
    for(Map<String,Object> row:nodes){String path=(String)row.get("path");if(path.contains("/Near Core Layer Aspect Ratio")||path.contains("/Prism Layer Reduction Percentage"))continue;flat.put(path+"|#class",(String)row.get("class"));
      for(var entry:((Map<String,Object>)row.get("properties")).entrySet()){
        String key=entry.getKey();if(skip.contains(key)||(path.equals(TARGET)&&Set.of("RelativeSize","AbsoluteSize").contains(key))||(path.endsWith("/Curve Control/Values/Target Surface Size")&&Set.of("RelativeSize","AbsoluteSize").contains(key))||(path.endsWith("/Meshers/Prism Layer Mesher")&&key.equals("EnhancedPrismLayers")))continue;
        Object value=entry.getValue();String text=value instanceof Number?new BigDecimal(value.toString()).stripTrailingZeros().toPlainString():String.valueOf(value);
        flat.put(path+"|"+key,text);
      }
    }return json(flat);
  }
  private static String sha(byte[] bytes)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}
  private static void require(boolean value,String message){if(!value)throw new IllegalStateException(message);}
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
