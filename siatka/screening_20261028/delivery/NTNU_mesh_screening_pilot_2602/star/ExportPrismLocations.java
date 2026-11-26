package macro;
import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.vis.*;
import java.nio.file.*;
import java.util.*;

/** Read-only-on-disk follow-up: locate detected reduced prism stacks on the foil. */
public class ExportPrismLocations extends StarMacro {
  public void execute(){
    Simulation s=getActiveSimulation();
    try{
      Path target=Paths.get(Objects.requireNonNull(System.getenv("NTNU_PRISM_SOURCE"))).toAbsolutePath().normalize();
      Path out=Paths.get(Objects.requireNonNull(System.getenv("NTNU_PRISM_OUTPUT"))).toAbsolutePath().normalize();
      Path allowed=Paths.get("F:/ntnu/mesh_screening_20261028").toAbsolutePath().normalize();
      if(!target.startsWith(allowed.resolve("pilot_v3"))||!out.startsWith(allowed)||!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(target))throw new IllegalStateException("Wrong source/output scope");
      if(Files.exists(out))throw new IllegalStateException("Output directory already exists; preserve earlier evidence");
      if(s.getSimulationIterator().getAutoSave().getEnabled()||s.getSimulationIterator().getAutoSave().getAutoSaveBatch())throw new IllegalStateException("Autosave unexpectedly enabled");
      int iteration=s.getSimulationIterator().getCurrentIteration();Files.createDirectories(out);
      Region region=s.getRegionManager().getRegion("fluid");Boundary foil=(Boundary)region.getBoundaryManager().getObject("HF_v2 2.ColoredFace1");
      FvRepresentation fv=(FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
      FieldFunctionManager fields=s.getFieldFunctionManager();
      if(!fields.hasFunction("PrismLayerNumber")||!fields.hasFunction("PrismCellThickness"))throw new IllegalStateException("Missing prism diagnostic fields");
      FieldFunction layer=fields.getFunction("PrismLayerNumber");FieldFunction thickness=fields.getFunction("PrismCellThickness");
      ThresholdPart reduced=s.getPartManager().createThresholdPart();reduced.setPresentationName("NTNU_reduced_prism_stacks_export");
      reduced.getInputParts().setObjects(foil);reduced.setFieldFunction(layer);reduced.setRange(new DoubleVector(new double[]{14.5,14.5}));reduced.setMode(ThresholdMode.BELOW_TAG);
      ElementCountReport count=s.getReportManager().createReport(ElementCountReport.class);count.setRepresentation(fv);count.getParts().setObjects(reduced);
      double n=count.getReportMonitorValue();if(!Double.isFinite(n)||n<0||n>1000000||!count.getErrorLog().isBlank())throw new IllegalStateException("Invalid or over-budget diagnostic population: "+n);
      if(n>0){XyzInternalTable table=s.getTableManager().createTable(XyzInternalTable.class);table.getParts().setObjects(reduced);table.setFieldFunctions(List.of(layer,thickness));table.setRepresentation(fv);table.setExtractVertexData(false);table.extract();table.export(out.resolve("reduced_prism_stacks.csv").toString());}
      String note="Source: "+target+"\nPopulation: foil boundary HF_v2 2.ColoredFace1, STAR PrismLayerNumber < 14.5.\nDetected element count: "+n+"\nFields: PrismLayerNumber, PrismCellThickness; the thickness field on the wall denotes detected total stack thickness.\nCoordinates: laboratory-frame non-vertex samples; do not infer area fraction from unweighted row counts.\nGeometric layer detection is not a direct proof of mesher collapse. Review against sections.\nNo mesh generation, solver iterations, or save of the source simulation was requested.\n";
      if(s.getSimulationIterator().getCurrentIteration()!=iteration)throw new IllegalStateException("Unexpected solver iteration");
      Files.writeString(out.resolve("README.txt"),note);Files.writeString(out.resolve("EXPORT_OK.txt"),"completed");s.println("[NTNU] PRISM_LOCATIONS_EXPORTED count="+n);
    }catch(Exception e){throw new RuntimeException(e);}
  }
}
