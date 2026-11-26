package macro;
import star.common.*;import java.nio.file.*;import java.util.*;
public class ImportExactM04 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path out=Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M04/repair_exact_extrusion");
try{
Files.writeString(out.resolve("pre_import_options.txt"),s.getImportManager().preImportQuery("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M04/repair_exact_extrusion/mesh_exact_extrusion.CGNS").toFormattedString());
s.getSimulationIterator().getAutoSave().setEnabled(false);
s.getImportManager().importMeshFiles(List.of("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M04/repair_exact_extrusion/mesh_exact_extrusion.CGNS"));
List<String> info=new ArrayList<>();
for(Region r:s.getRegionManager().getRegions()){info.add("REGION "+r.getPresentationName());for(Boundary b:r.getBoundaryManager().getBoundaries())info.add(b.getPresentationName()+" : "+b.getBoundaryType().getClass().getName());}
Files.write(out.resolve("imported_boundaries.txt"),info);
star.common.FvRepresentation fv=(star.common.FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
Files.writeString(out.resolve("mesh_report.txt"),fv.generateMeshReport(new ArrayList<Region>(s.getRegionManager().getRegions())).toFormattedString());
s.saveState(out.resolve("imported_probe.sim").toString());
Files.writeString(out.resolve("import_ok.txt"),"Import complete; boundary identity requires verification.");
}catch(Exception e){try{Files.writeString(out.resolve("import_error.txt"),e.toString());}catch(Exception ignored){}throw new RuntimeException(e);}
}}