package macro;

import java.nio.file.*;
import java.util.*;
import star.common.*;
import star.base.neo.*;
import star.flow.*;
import star.kwturb.*;

public class VerifyComeback extends StarMacro {
    private void export(Simulation sim, Path out, String file, NamedObject part, List<FieldFunction> fields) {
        XyzInternalTable table = sim.getTableManager().createTable(XyzInternalTable.class);
        table.getParts().setObjects(part);
        table.setFieldFunctions(fields);
        table.extract();
        table.export(out.resolve(file).toString(), ",");
    }

    public void execute() {
        Simulation sim = getActiveSimulation();
        try {
            Path out = Path.of(System.getenv("MINI_CASE_DIR"));
            Path copy = out.resolve("input.sim").toAbsolutePath().normalize();
            if (!Path.of(sim.getSessionPath()).toAbsolutePath().normalize().equals(copy))
                throw new IllegalStateException("Expected a dedicated checkpoint copy");
            Region region = sim.getRegionManager().getRegions().iterator().next();
            PhysicsContinuum physics = region.getPhysicsContinuum();
            FvRepresentation mesh = (FvRepresentation) sim.getRepresentationManager().getObject("Volume Mesh");
            if (sim.getNumberOfGpgpus() != 0 || mesh.getCellCount() != 9638)
                throw new IllegalStateException("Unexpected checkpoint identity");
            double reference = physics.getReferenceValues().get(ReferencePressure.class).getSIValue();
            FieldFunctionManager f = sim.getFieldFunctionManager();
            FieldFunction velocity = f.getFunction("Velocity");
            FieldFunction p = f.getFunction("Pressure");
            FieldFunction abs = f.getFunction("AbsolutePressure");
            export(sim, out, "cells.csv", region, List.of(p, abs, velocity.getComponentFunction(0),
                velocity.getComponentFunction(1), f.getFunction("Volume"), f.getFunction("LeastSquaresQuality"),
                f.getFunction("FaceValidity"), f.getFunction("TurbulentKineticEnergy"),
                f.getFunction("SpecificDissipationRate"), f.getFunction("TurbulentViscosityRatio")));
            double u = Double.NaN;
            for (Boundary b : region.getBoundaryManager().getBoundaries()) {
                String n = b.getPresentationName();
                if (n.contains("inlet"))
                    u = b.getValues().get(VelocityProfile.class).getMethod(ConstantVectorProfileMethod.class).getQuantity().getSIVector().get(0);
                if (n.contains("main") || n.contains("flap"))
                    export(sim, out, n.contains("main") ? "main_wall.csv" : "flap_wall.csv",
                           b, List.of(p, abs, f.getFunction("WallYplus")));
            }
            Files.writeString(out.resolve("REOPEN.json"),
                "{\"reference_pressure_Pa\":" + reference + ",\"U_m_s\":" + u +
                ",\"physical_time_s\":" + sim.getSolution().getPhysicalTime() + ",\"cells\":" + mesh.getCellCount() +
                ",\"SST\":" + (physics.getModelManager().hasModel(SstKwTurbModel.class)!=null) +
                ",\"all_yplus\":" + (physics.getModelManager().hasModel(KwAllYplusWallTreatment.class)!=null) +
                ",\"steps\":0}");
        } catch (Exception e) {
            throw new RuntimeException(e);
        } finally {
            if ("1".equals(System.getenv("COMEBACK_OWN_SESSION")))
                sim.close(ServerConnection.CloseOption.Close);
        }
    }
}


