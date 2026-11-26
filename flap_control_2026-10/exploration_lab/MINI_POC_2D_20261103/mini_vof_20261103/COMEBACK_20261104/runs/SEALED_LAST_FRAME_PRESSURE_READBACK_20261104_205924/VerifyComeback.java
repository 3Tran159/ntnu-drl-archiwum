package macro;
import java.nio.file.*;
import java.util.*;
import star.common.*;
import star.base.neo.*;
import star.vis.*;

public class VerifyComeback extends StarMacro {
    void export(Simulation s, Path out, NamedObject part, String name, FieldFunction pressure) {
        XyzInternalTable table = s.getTableManager().createTable(XyzInternalTable.class);
        table.getParts().setObjects(part);
        table.setFieldFunctions(List.of(pressure));
        table.extract();
        table.export(out.resolve(name).toString(), ",");
    }

    public void execute() {
        Simulation s = getActiveSimulation();
        Path out = Paths.get(System.getenv("MINI_CASE_DIR"));
        try {
            double time = s.getSolution().getPhysicalTime();
            FvRepresentation mesh = (FvRepresentation)s.getRepresentationManager().getObject("Volume Mesh");
            if (Math.abs(time - 1.250) > 1e-9 || mesh.getCellCount() != 17462 || s.getNumberOfGpgpus() != 0)
                throw new IllegalStateException("Unexpected pressure readback checkpoint");
            Files.writeString(out.resolve("native_status.json"),
                "{\"solver_state\":\"STOPPED\",\"operation\":\"PRESSURE_EXPORT\",\"time_s\":"+time+"}");
            Region region = s.getRegionManager().getRegions().iterator().next();
            FieldFunction pressure = s.getFieldFunctionManager().getFunction("AbsolutePressure");
            export(s,out,region,"pressure_cells.csv",pressure);
            for (Boundary boundary : region.getBoundaryManager().getBoundaries()) {
                String name = boundary.getPresentationName().toLowerCase(Locale.ROOT);
                if (name.contains("main") || name.contains("flap"))
                    export(s,out,boundary,name.contains("flap") ? "pressure_flap.csv" : "pressure_main.csv",pressure);
            }
            try {
                Scene scene = s.getSceneManager().createScene("Sharp sealed absolute pressure");
                scene.initializeAndWait();
                ScalarDisplayer field = scene.getDisplayerManager().createScalarDisplayer("Absolute pressure");
                field.getInputParts().setObjects(region);
                field.setRepresentation(mesh);
                field.getScalarDisplayQuantity().setFieldFunction(pressure);
                field.getScalarDisplayQuantity().setRangeMin(0);
                field.getScalarDisplayQuantity().setRangeMax(200000);
                scene.getCurrentView().setInput(new DoubleVector(new double[]{1.03,.02,0}),
                    new DoubleVector(new double[]{1.03,.02,2}), new DoubleVector(new double[]{0,1,0}),
                    .30, 1, s.getCoordinateSystemManager().getLabCoordinateSystem(), false);
                scene.printAndWait(out.resolve("native_pressure.png").toString(),1,1600,1000);
            } catch (Exception sceneError) {
                Files.writeString(out.resolve("scene_error.txt"),sceneError.toString());
            }
            if (s.getSolution().getPhysicalTime() != time)
                throw new IllegalStateException("Pressure readback changed the simulation time");
            Files.writeString(out.resolve("REOPEN.json"),
                "{\"time_s\":"+time+",\"cells\":17462,\"solver_steps\":0}");
        } catch (Exception failure) {
            throw new RuntimeException(failure);
        }
    }
}

