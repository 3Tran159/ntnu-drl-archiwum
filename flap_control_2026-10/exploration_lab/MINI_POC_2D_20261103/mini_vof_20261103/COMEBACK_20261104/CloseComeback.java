package macro;
import star.base.neo.ServerConnection;
import star.common.*;
import java.nio.file.*;

public class CloseComeback extends StarMacro {
 public void execute() {
  Simulation s=getActiveSimulation();
  Path cwd=Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
  Path expected=Path.of(System.getenv("MINI_CASE_DIR")).toAbsolutePath().normalize();
  if(!cwd.equals(expected)||!Files.isRegularFile(expected.resolve("job.properties")))
   throw new IllegalStateException("Unexpected diagnostic directory");
  s.close(ServerConnection.CloseOption.Close);
 }
}

