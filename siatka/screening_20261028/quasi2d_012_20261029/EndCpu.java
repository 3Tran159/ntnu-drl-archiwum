package macro;
import star.common.*;import java.nio.file.*;
public class EndCpu extends StarMacro {public void execute(){try{Files.writeString(Paths.get("F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/END_SESSION"),"CPU pilot mesh sequence completed");}catch(Exception e){throw new RuntimeException(e);}}}
