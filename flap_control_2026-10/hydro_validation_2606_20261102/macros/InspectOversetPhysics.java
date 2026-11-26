package macro;
import star.common.*;import star.base.neo.*;import star.base.report.*;import star.overset.*;import java.nio.file.*;import java.util.*;
public class InspectOversetPhysics extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),out=root.resolve("audit/overset_physics_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{
if(!input.startsWith(root.resolve("cases/SP_C_split0_overset")))throw new IllegalStateException("Owned Overset source only");
Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
if(!s.getSolution().isInitialized())s.getSolution().initializeSolution();
StringBuilder fields=new StringBuilder();List<FieldFunction> ff=new ArrayList<>();for(String name:List.of("Pressure","AbsolutePressure","Volume","CellQuality"))ff.add(s.getFieldFunctionManager().getFunction(name));
for(FieldFunction f:s.getFieldFunctionManager().getObjects())if(f.getPresentationName().startsWith("Overset")){fields.append(f.getPresentationName()+" : "+f.getFunctionName()+"\n");if(List.of("Overset Cell Status","Overset Cell Type","Overset Error Status","Overset Interpolation Cell Size Ratio","Overset Interpolation Type").contains(f.getPresentationName()))ff.add(f);}
Files.writeString(out.resolve("fields.txt"),fields.toString());
UserFieldFunction one=s.getFieldFunctionManager().createFieldFunction();one.setPresentationName("Inspection one");one.setFunctionName("InspectionOne");one.getTypeOption().setSelected(FieldFunctionTypeOption.Type.SCALAR);one.setDimensions(new Dimensions());one.setDefinition("1");
StringBuilder audit=new StringBuilder("source="+input+"\ntime="+s.getSolution().getPhysicalTime()+"\n");
PhysicsContinuum pc=(PhysicsContinuum)s.getContinuumManager().getObject("HYDRO water SST singlephase");audit.append("conservation="+pc.getModelManager().getModel(OversetConservationModel.class).getOversetConservationOption().getSelected()+"\n");
for(String name:List.of("Background","FlapOverset")){Region r=s.getRegionManager().getRegion(name);
for(String repName:List.of("Volume Mesh","Overset Mesh")){Representation rep=(Representation)s.getRepresentationManager().getObject(repName);
XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(r);table.setRepresentation(rep);table.setExtractVertexData(false);table.setFieldFunctions(ff);table.extract();table.export(out.resolve(name+"_"+repName.replace(" ","_")+".csv").toString());
for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){SurfaceIntegralReport area=s.getReportManager().createReport(SurfaceIntegralReport.class);area.setFieldFunction(one);area.getParts().setObjects(b);area.setRepresentation(rep);audit.append(name+" | "+repName+" | "+b.getPresentationName()+" | area="+area.getReportMonitorValue()+"\n");s.getReportManager().removeObjects(area);}
}}
Files.writeString(out.resolve("audit.txt"),audit.toString());Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"simulation_saved\":false,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
