package macro;
import star.common.*;import star.flow.*;import star.base.report.*;import star.post.*;
import java.nio.file.*;import java.util.*;
/** Read-only field audit: no initialization, steps or saveState calls. */
public class AuditTemporalMassR2 extends StarMacro {
 public void execute(){Simulation s=getActiveSimulation();
 try{
  Path src=Paths.get(s.getSessionPath()).toAbsolutePath().normalize();
  Path allowed=Paths.get("E:/ntnu/temporal_conservation_20261029/r2").toAbsolutePath().normalize();
  if(!src.getParent().equals(allowed))throw new IllegalStateException("Only dedicated audit copies allowed");
  Path out=allowed.resolve(src.getFileName().toString().replace(".sim","_audit.json"));
  if(Files.exists(out))throw new IllegalStateException("Existing audit preserved");
  boolean initializedFlag=s.getSolution().isInitialized();
  double t=s.getSolution().getPhysicalTime();
  s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
  for(SolutionHistory h:s.get(SolutionHistoryManager.class).getSolutionHistories())h.setAutoRecord(false);
  Region r=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  Map<String,Object>d=new LinkedHashMap<>();d.put("source_copy",src.toString());d.put("time_s",t);d.put("steps_taken",0);d.put("source_saved",false);d.put("cells",fv.getCellCount());d.put("gpu_count",s.getNumberOfGpgpus());d.put("initialized_flag_on_load",initializedFlag);
  Boundary foil=r.getBoundaryManager().getBoundary("HF_012_wall");
  ForceReport force=s.getReportManager().createReport(ForceReport.class);force.getParts().setObjects(foil);force.setRepresentation(fv);force.getForceOption().setSelected(ForceReportForceOption.Type.PRESSURE_AND_SHEAR);force.getDirection().setComponents(1,0,0);d.put("saved_Fx_N",force.getReportMonitorValue());force.getDirection().setComponents(0,0,1);d.put("saved_Fz_N",force.getReportMonitorValue());
  FieldFunction alpha=s.getFieldFunctionManager().getFunction("VolumeFractionwater"),rho=s.getFieldFunctionManager().getFunction("Density");
  VolumeIntegralReport v=s.getReportManager().createReport(VolumeIntegralReport.class);v.getParts().setObjects(r);v.setRepresentation(fv);v.setFieldFunction(alpha);d.put("water_volume_m3",v.getReportMonitorValue());v.setFieldFunction(rho);d.put("mixture_mass_kg",v.getReportMonitorValue());
  List<Object> bounds=new ArrayList<>();double net=0,in=0,outward=0;
  for(Boundary b:r.getBoundaryManager().getBoundaries()){
   MassFlowReport q=s.getReportManager().createReport(MassFlowReport.class);q.getParts().setObjects(b);q.setRepresentation(fv);
   double flux=q.getReportMonitorValue();if(!Double.isFinite(flux))throw new IllegalStateException("Nonfinite mass flux");
   bounds.add(Map.of("boundary",b.getPresentationName(),"type",b.getBoundaryType().getClass().getSimpleName(),"mass_flow_kg_s",flux));net+=flux;if(flux<0)in-=flux;else outward+=flux;
  }
  d.put("boundary_mass_fluxes",bounds);d.put("net_outward_mass_flow_kg_s",net);d.put("inward_mass_flow_magnitude_kg_s",in);d.put("outward_mass_flow_kg_s",outward);d.put("net_relative_to_inlet_pct",in>0?100*net/in:null);
  d.put("limitation","Instantaneous solver mass-flow reports only. Unsteady accumulation and phase-flux history are required for a full conservation budget.");
  if(s.getSolution().getPhysicalTime()!=t)throw new IllegalStateException("Time changed");
  Files.writeString(out,json(d));s.println("[NTNU_MASS_AUDIT] completed without steps or source save");
 }catch(Exception e){throw new RuntimeException("[NTNU_MASS_AUDIT] "+e,e);}}
 private String json(Object o){if(o==null)return "null";if(o instanceof Number)return Double.isFinite(((Number)o).doubleValue())?o.toString():"null";if(o instanceof Boolean)return o.toString();if(o instanceof Map){StringJoiner j=new StringJoiner(",","{","}");for(Map.Entry<?,?>e:((Map<?,?>)o).entrySet())j.add(json(e.getKey().toString())+":"+json(e.getValue()));return j.toString();}if(o instanceof Iterable){StringJoiner j=new StringJoiner(",","[","]");for(Object a:(Iterable<?>)o)j.add(json(a));return j.toString();}return "\""+o.toString().replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";}
}
