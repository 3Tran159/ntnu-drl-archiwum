package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.vis.*;import star.post.*;import java.nio.file.*;import java.util.*;
public class FlowHotspots012 extends StarMacro{
 public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/mesh_screening_20261028/flow012_short_20261029"),out=root.resolve("postprocess");
 try{
  if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(root.resolve("F18_18ms/checkpoint.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Read-only checkpoint guard");
  Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);s.getSimulationIterator().getAutoSave().setEnabled(false);
  Region fluid=s.getRegionManager().getRegion("fluid");FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
  if(fv.getCellCount()!=1165391)throw new IllegalStateException("Wrong cells");
  int iter=s.getSimulationIterator().getCurrentIteration();double time=s.getSolution().getPhysicalTime();
  FieldFunction velocity=s.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction(),cfl=s.getFieldFunctionManager().getFunction("CourantNumber");
  StringBuilder result=new StringBuilder("{\"iteration\":"+iter+",\"physical_time_s\":"+time+",\"cells\":"+fv.getCellCount());
  for(int i=0;i<2;i++){
   String label=i==0?"velocity_above_36":"cfl_above_2";FieldFunction ff=i==0?velocity:cfl;double cutoff=i==0?36:2;
   ThresholdPart part=s.getPartManager().createThresholdPart();part.getInputParts().setObjects(fluid);part.setFieldFunction(ff);part.setRange(new DoubleVector(new double[]{cutoff,cutoff}));part.setMode(ThresholdMode.ABOVE_TAG);
   ElementCountReport n=s.getReportManager().createReport(ElementCountReport.class);n.getParts().setObjects(part);n.setRepresentation(fv);double count=n.getReportMonitorValue();
   result.append(",\""+label+"_count\":"+count);
   if(count>0 && count<100000){XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(part);table.setRepresentation(fv);table.setExtractVertexData(false);
    List<FieldFunction> f=new ArrayList<>(List.of(velocity,cfl));for(String key:List.of("CellQuality","SkewnessAngle","VolumeChange","PrismLayerNumber"))f.add(s.getFieldFunctionManager().getFunction(key));
    table.setFieldFunctions(f);table.extract();table.export(out.resolve(label+".csv").toString());
   }
  }
  result.append(",\"solver_steps_executed\":0}");Files.writeString(out.resolve("hotspots.json"),result.toString());
  if(iter!=s.getSimulationIterator().getCurrentIteration()||time!=s.getSolution().getPhysicalTime())throw new IllegalStateException("Unexpected solver progress");
  s.println("SHORT012_POSTPROCESS_DONE no solver steps; checkpoint not overwritten");
 }catch(Exception e){throw new RuntimeException(e);}
 }
}
