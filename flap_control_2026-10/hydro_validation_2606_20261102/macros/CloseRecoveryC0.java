package macro;
import star.common.*;import star.base.neo.*;import java.nio.file.*;
public class CloseRecoveryC0 extends StarMacro {
public void execute(){Simulation s=getActiveSimulation();Path h=Paths.get("F:/ntnu/flap_control/hydro_validation_2606_20261102");
if(!s.getSessionPath().contains("relocation_reopen_20261103_082325")||Math.abs(s.getSolution().getPhysicalTime()-.65)>1e-9||s.getSimulationIterator().getCurrentIteration()!=11560||!Files.exists(h.resolve("audit/relocation_native_20261103_C0/status.json")))throw new IllegalStateException("Owned read-only recovery session required");
// Native STAR server close, after verified read-only audit. No OS process kill.
s.close(ServerConnection.CloseOption.ForceClose);
}}
