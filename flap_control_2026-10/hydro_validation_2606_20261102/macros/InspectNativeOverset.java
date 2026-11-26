package macro;
import star.common.*;import star.base.report.*;import star.base.neo.*;import star.overset.*;import java.nio.file.*;import java.util.*;
public class InspectNativeOverset extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),out=root.resolve("audit/native_overset_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{
if(!input.startsWith(root.resolve("cases/SP_C_split0_overset")))throw new IllegalStateException("Own copy only");
Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
double time=s.getSolution().getPhysicalTime();StringBuilder info=new StringBuilder("source="+input+"\nsaved_time="+time+"\n");
List<Region> regions=new ArrayList<>();regions.add(s.getRegionManager().getRegion("Background"));regions.add(s.getRegionManager().getRegion("FlapOverset"));
List<FieldFunction> ff=new ArrayList<>();for(String n:List.of("Volume","CellQuality","OversetCellStatus","OversetCellType","OversetErrorStatus","OversetInterpolationType","Overset Interpolation Cell Size Ratio"))ff.add(s.getFieldFunctionManager().getFunction(n));
for(Representation r:s.getRepresentationManager().getObjects()){info.append(r.getPresentationName()+" class="+r.getClass().getName());if(r instanceof FullMeshViewRepresentation)info.append(" underlying="+((FullMeshViewRepresentation)r).getFvRepresentation()+" empty="+((FullMeshViewRepresentation)r).isEmpty());info.append("\n");}
PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");info.append("flux_conservation="+pc.getModelManager().getModel(OversetConservationModel.class).getOversetConservationOption().getSelected()+"\n");
Representation full=(Representation)s.getRepresentationManager().getObject("Overset Mesh");
List<Representation> reps=new ArrayList<>();reps.add((Representation)s.getRepresentationManager().getObject("Volume Mesh"));reps.add(full);if(full instanceof FullMeshViewRepresentation)reps.add(((FullMeshViewRepresentation)full).getFvRepresentation());
for(int i=0;i<reps.size();i++){Representation rep=reps.get(i);info.append("TEST "+i+" "+rep+"\n");
for(Region region:regions){for(String name:List.of("Volume","OversetCellStatus","OversetCellType","OversetErrorStatus","OversetInterpolationType")){
MinReport low=s.getReportManager().createReport(MinReport.class);MaxReport high=s.getReportManager().createReport(MaxReport.class);low.getParts().setObjects(region);high.getParts().setObjects(region);low.setRepresentation(rep);high.setRepresentation(rep);low.setFieldFunction(s.getFieldFunctionManager().getFunction(name));high.setFieldFunction(s.getFieldFunctionManager().getFunction(name));info.append(region+" "+name+" min="+low.getReportMonitorValue()+" max="+high.getReportMonitorValue()+"\n");s.getReportManager().removeObjects(low,high);}
XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(region);table.setRepresentation(rep);table.setExtractVertexData(false);table.setFieldFunctions(ff);table.extract();table.export(out.resolve(region.getPresentationName()+"_representation_"+i+".csv").toString());
}}
Files.writeString(out.resolve("diagnostic.txt"),info.toString());if(s.getSolution().getPhysicalTime()!=time)throw new IllegalStateException("Read-only inspection advanced time");
Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"simulation_saved\":false,\"physical_time_preserved\":true,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
