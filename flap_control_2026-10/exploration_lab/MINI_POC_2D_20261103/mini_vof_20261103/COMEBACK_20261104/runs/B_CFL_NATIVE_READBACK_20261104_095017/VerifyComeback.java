package macro;
import star.common.*;
import star.base.report.*;
import java.nio.file.*;
import java.util.*;

public class VerifyComeback extends StarMacro {
 public void execute() {
  Simulation s=getActiveSimulation();
  try {
   Path out=Path.of(System.getenv("MINI_CASE_DIR"));
   Path expected=out.resolve("input.sim").toAbsolutePath().normalize();
   if(!Path.of(s.getSessionPath()).toAbsolutePath().normalize().equals(expected))
    throw new IllegalStateException("Unexpected verification input");
   Properties cfg=new Properties();
   try(var r=Files.newBufferedReader(out.resolve("job.properties"))){cfg.load(r);}
   if(Boolean.parseBoolean(cfg.getProperty("cfl_probe","false"))){
    Region region=s.getRegionManager().getRegions().iterator().next();
    FieldFunctionManager fm=s.getFieldFunctionManager();
    FieldFunction position=fm.getFunction("Position"),velocity=fm.getFunction("Velocity"),cfl=fm.getFunction("CourantNumber");
    List<FieldFunction> samples=new ArrayList<>(List.of(position.getComponentFunction(0),position.getComponentFunction(1),position.getComponentFunction(2),
     velocity.getComponentFunction(0),velocity.getComponentFunction(1),velocity.getComponentFunction(2),fm.getFunction("Volume")));
    for(String field:List.of("GridVelocity","MeshVelocity")){
     FieldFunction v=fm.getFunction(field);
     if(v!=null){for(int j=0;j<3;j++)samples.add(v.getComponentFunction(j));break;}
    }
    MaxReport max=s.getReportManager().createReport(MaxReport.class);
    max.setFieldFunction(cfl);max.getParts().setObjects(region);max.setSmooth(false);max.setCollocatedFieldFunctions(samples);
    double value=max.getReportMonitorValue();
    StringBuilder report=new StringBuilder("field,value\n");
    report.append("max_CFL,").append(value).append("\n");
    for(FieldFunction sample:samples)
     report.append(sample.getPresentationName()).append(",").append(max.getCollocatedValue(sample)).append("\n");
    Files.writeString(out.resolve("CFL_MAX_COLLOCATION.csv"),report.toString());
    XyzInternalTable tab=s.getTableManager().createTable(XyzInternalTable.class);
    tab.getParts().setObjects(region);
    List<FieldFunction> export=new ArrayList<>();export.add(cfl);export.addAll(samples);
    tab.setFieldFunctions(export);tab.extract();tab.export(out.resolve("cell_cfl.csv").toString(),",");
    Files.writeString(out.resolve("REOPEN.json"),"{\"time_s\":"+s.getSolution().getPhysicalTime()+",\"diagnostic\":\"CFL read only\",\"steps\":0}");
    return;
   }
   XyzInternalTable f=(XyzInternalTable)s.getTableManager().getTable("NIGHT_FIELDS");
   f.extract();
   f.export(out.resolve("reopened_fields.csv").toString(),",");
   StringBuilder normal=new StringBuilder("monitor,normalization_type,factor,normalized,samples,last_stored\n");
   for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r){
    double[] history=r.getAllYValues();
    normal.append(r.getPresentationName()).append(",").append(r.getNormalizationType().getClass().getSimpleName()).append(",")
     .append(r.getNormalizationType().getNormalizationFactor()).append(",").append(r.isNormalized()).append(",")
     .append(history.length).append(",").append(history.length==0?Double.NaN:history[history.length-1]).append("\n");
   }
   Files.writeString(out.resolve("RESIDUAL_NORMALIZATION.csv"),normal.toString());
   double t=s.getSolution().getPhysicalTime();
   long cells=((FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh")).getCellCount();
   Files.writeString(out.resolve("REOPEN.json"),"{\"time_s\":"+t+",\"cells\":"+cells+"}");
  }catch(Exception e){throw new RuntimeException(e);}
 }
}



