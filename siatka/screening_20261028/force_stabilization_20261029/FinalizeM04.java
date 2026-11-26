package macro;
import star.common.*;import star.flow.*;import star.base.neo.*;import java.nio.file.*;import java.util.*;
public class FinalizeM04 extends StarMacro {
public void execute(){
Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M04_verified");
try{
Files.createDirectories(out);
Region old=s.getRegionManager().getRegion("fluid"),fresh=s.getRegionManager().getRegion("fluid 2");
fresh.setPhysicsContinuum(old.getPhysicsContinuum());
List<String> audit=new ArrayList<>();
for(Boundary b:old.getBoundaryManager().getBoundaries()){
 Boundary n=fresh.getBoundaryManager().getBoundary(b.getPresentationName());
 String name=n.getPresentationName();n.copyProperties(b);n.setPresentationName(name);
 if(!n.getBoundaryType().getClass().equals(b.getBoundaryType().getClass()))throw new IllegalStateException("Boundary type mismatch");
 audit.add(name+" : "+n.getBoundaryType().getClass().getName());
}
String inlet=fresh.getBoundaryManager().getBoundary("DOMAIN.inlet").getValues().get(VelocityProfile.class).getMethod(FunctionVectorProfileMethod.class).getFieldFunction().getPresentationName();
if(!inlet.equals("Velocity of Calm"))throw new IllegalStateException("Inlet velocity was not preserved: "+inlet);
if(!fresh.getPhysicsContinuum().getPresentationName().equals("water+air"))throw new IllegalStateException("Physics continuum mismatch");
s.getRegionManager().removeObjects(List.of(old));fresh.setPresentationName("fluid");
FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
if(fv.getCellCount()!=138468)throw new IllegalStateException("Unexpected cell count after removing old region: "+fv.getCellCount());
NeoProperty report=fv.generateMeshReport(List.of(fresh));Files.writeString(out.resolve("precheck_mesh_report.txt"),report.toFormattedString());
Files.write(out.resolve("boundary_transfer_audit.txt"),audit);
s.saveState(out.resolve("clean_import.sim").toString());
StarScript script=new StarScript(s,Paths.get("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029/AuditVerifiedM04.java").toFile());script.play();
if(script.getInterruptedByException())throw new IllegalStateException("Quality audit failed");
Files.writeString(out.resolve("finalization_ok.txt"),"Physics and boundary settings transferred; original warped region removed; independent quality audit exported.");
}catch(Exception e){try{Files.writeString(out.resolve("finalize_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}
