package macro;
import star.common.*;import star.vis.*;import star.base.neo.*;import star.base.report.*;import java.nio.file.*;import java.io.*;import java.util.*;
public class InspectC0LayerFailure extends StarMacro{
public void execute(){Simulation s=getActiveSimulation();Path root=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102"),input=Paths.get(s.getSessionPath()).toAbsolutePath().normalize(),out=root.resolve("cases/SP_C_split0_overset/c0_layers36_error_audit_"+System.getenv("NTNU_HYDRO_RUN_ID"));
try{
if(!input.equals(root.resolve("cases/SP_C_split0_overset/c0_layers36_zero_storage_20261103_021548/layer_audit_error.sim")))throw new IllegalStateException("Only failed owned mesh audit allowed");
java.security.MessageDigest md=java.security.MessageDigest.getInstance("SHA-256");try(InputStream f=Files.newInputStream(input)){byte[] b=new byte[1048576];int n;while((n=f.read(b))!=-1)md.update(b,0,n);}
if(!java.util.HexFormat.of().formatHex(md.digest()).equals("f80624ba9f078d2af01dd4d4f50f68ed751f24b548f0274615d1dcf0211f42ab"))throw new IllegalStateException("Source fingerprint changed");
Files.createDirectories(out);s.getSimulationIterator().getAutoSave().setEnabled(false);s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
double time=s.getSolution().getPhysicalTime();int iteration=s.getSimulationIterator().getCurrentIteration();
Representation full=s.getRepresentationManager().getObject("Overset Mesh");StringBuilder info=new StringBuilder("source="+input+"\nphysical_time="+time+"\nnative_iteration="+iteration+"\n");
List<FieldFunction> fields=new ArrayList<>();for(String name:List.of("OversetCellStatus","OversetErrorStatus","OversetInterpolationType","Volume","CellQuality"))fields.add(s.getFieldFunctionManager().getFunction(name));
for(String name:List.of("Background","FlapOverset")){Region r=s.getRegionManager().getRegion(name);PlaneSection p=s.getPartManager().createImplicitPart(List.of(r),List.of(0.,1.,0.),List.of(0.,.02,0.),0,1,new DoubleVector(new double[]{0}));
XyzInternalTable t=s.getTableManager().createTable(XyzInternalTable.class);t.getParts().setObjects(p);t.setRepresentation(full);t.setExtractVertexData(false);t.setFieldFunctions(fields);t.extract();t.export(out.resolve(name+"_failed_full_plane.csv").toString());
for(Boundary b:r.getBoundaryManager().getBoundaries())if(b.getBoundaryType() instanceof WallBoundary&&!b.getPresentationName().endsWith("bottom")){info.append(name+" wall="+b.getPresentationName()+" dynamic="+b.getConditions().get(DynamicOversetBehaviour.class).getSelected());try{info.append(" activeLayers="+b.getValues().get(NumActiveLayers.class).getNumLayers());}catch(Exception e){info.append(" no_activeLayers");}info.append("\n");}}
for(Interface iface:s.getInterfaceManager().getObjects())if(iface instanceof IndirectRegionInterface){IndirectRegionInterface i=(IndirectRegionInterface)iface;info.append("interface="+i.getPresentationName()+" alternate="+i.getUseAlternateHoleCutting()+" close="+i.getCloseProximity()+" prism_shrink="+i.getPrismLayerShrinkage()+" errors_as_warning="+i.getTreatErrorAsWarning()+"\n");}
Files.writeString(out.resolve("native_settings.txt"),info.toString());
if(s.getSimulationIterator().getCurrentIteration()!=iteration||s.getSolution().getPhysicalTime()!=time)throw new IllegalStateException("Inspection changed counters");
Files.writeString(out.resolve("status.json"),"{\"status\":\"inspection_complete\",\"solver_steps\":0,\"simulation_saved\":false,\"scientific_approved\":false,\"training_approved\":false}");
}catch(Exception e){try{Files.writeString(out.resolve("error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
