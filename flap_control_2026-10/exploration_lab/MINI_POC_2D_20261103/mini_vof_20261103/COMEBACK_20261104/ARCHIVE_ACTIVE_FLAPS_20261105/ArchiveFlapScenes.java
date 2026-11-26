package macro;

import java.nio.file.*;
import java.util.*;
import star.base.neo.*;
import star.common.*;
import star.vis.*;

public class ArchiveFlapScenes extends StarMacro {
    Simulation sim;
    Path out;
    FvRepresentation mesh;
    Region region;
    List<Boundary> foil;
    FieldFunction velocity, pressure;
    DoubleVector vector(double x,double y,double z){return new DoubleVector(new double[]{x,y,z});}

    Scene scene(String name,double x,double halfHeight) {
        Scene sc=sim.getSceneManager().createScene(name);
        sc.initializeAndWait();
        sc.getCurrentView().setInput(vector(x,.02,0),vector(x,.02,3),vector(0,1,0),
              halfHeight,1,sim.getCoordinateSystemManager().getLabCoordinateSystem(),false);
        return sc;
    }

    void outline(Scene sc) {
        PartDisplayer wall=sc.getDisplayerManager().createPartDisplayer("Main foil and flap");
        wall.getInputParts().setObjects(foil);
        wall.setRepresentation(mesh);
        wall.setOutline(true);
        wall.setMesh(true);
    }

    void export(Scene scene,String file) {
        scene.printAndWait(out.resolve(file).toString(),1,1450,820);
    }

    void plots(Table table,String name,String x,String... ys) {
        XYPlot plot=sim.getPlotManager().createXYPlot(name);
        plot.setTitle(name);
        for(String y:ys){
            ExternalDataSet data=plot.getDataSetManager().createExternalDataSet(plot);
            data.setTable(table);
            data.setXValuesName(x);
            data.setYValuesName(y);
            data.setPresentationName(y);
        }
        plot.initialize();
    }

    public void execute() {
        sim=getActiveSimulation();
        try {
            out=Paths.get(System.getenv("FLAP_POST_DIR"));
            double initial=sim.getSolution().getPhysicalTime();
            double expected=Double.parseDouble(System.getenv("FLAP_POST_TIME"));
            if(Math.abs(initial-expected)>1e-9||sim.getNumberOfGpgpus()!=0)throw new IllegalStateException("Unexpected checkpoint time or GPU");
            region=sim.getRegionManager().getRegions().iterator().next();
            mesh=(FvRepresentation)sim.getRepresentationManager().getObject("Volume Mesh");
            foil=new ArrayList<>();
            for(Boundary b:region.getBoundaryManager().getBoundaries()){
                String n=b.getPresentationName().toLowerCase(Locale.ROOT);
                if(n.contains("main")||n.contains("flap"))foil.add(b);
            }
            if(foil.size()!=2)throw new IllegalStateException("Missing foil boundaries");
            velocity=sim.getFieldFunctionManager().getFunction("Velocity");
            pressure=sim.getFieldFunctionManager().getFunction("AbsolutePressure");
            Scene geo=scene("AF 01 - Hydrofoil geometry",.60,.35);
            outline(geo);export(geo,"geometry.png");

            StreamPart lines=sim.getPartManager().createStreamPart();
            lines.setPresentationName("AF - Upstream streamline seeds");
            lines.getInputParts().setObjects(region);

            lines.setFieldFunction(velocity);
            lines.setMode(SeedMode.LINE);
            LineSeed seed=lines.getLineSeed();
            seed.setPoint1(vector(-.38,-.38,0));seed.setPoint2(vector(-.38,.42,0));seed.setResolution(51);
            lines.getIntegrator().setDirection(IntegrationDirection.FORWARD);
            lines.getIntegrator().setMaximumNumberOfSteps(2500);
            Scene flow=scene("AF 02 - Streamlines colored by speed",.57,.51);
            StreamDisplayer stream=flow.getDisplayerManager().createStreamDisplayer("Speed on streamlines");
            stream.getInputParts().setObjects(lines);
            stream.setRepresentation(mesh);
            stream.setMode(StreamDisplayerMode.LINES);
            stream.setColorMode(StreamColorMode.SCALAR);
            stream.getScalarDisplayQuantity().setFieldFunction(velocity.getMagnitudeFunction());
            stream.getScalarDisplayQuantity().setRangeMin(0);stream.getScalarDisplayQuantity().setRangeMax(30);
            outline(flow);export(flow,"streamlines_velocity.png");

            Scene ps=scene("AF 03 - Absolute pressure",.60,.42);
            ScalarDisplayer pd=ps.getDisplayerManager().createScalarDisplayer("Absolute pressure");
            pd.getInputParts().setObjects(region);
            pd.setRepresentation(mesh);
            pd.getScalarDisplayQuantity().setFieldFunction(pressure);
            pd.getScalarDisplayQuantity().setRangeMin(0);pd.getScalarDisplayQuantity().setRangeMax(200000);
            export(ps,"absolute_pressure.png");

            Table table=sim.getTableManager().createFromFile(out.resolve("trajectory.csv").toString());
            table.setPresentationName("AF - Archived transient cycle");
            int expectedRows=Integer.parseInt(System.getenv("FLAP_POST_ROWS"));
            if(table.getRowCount()!=expectedRows)throw new IllegalStateException("History table row count: "+table.getRowCount());
            plots(table,"AF 01 - Flap deflection vs elapsed time","elapsed_s","measured_deg","command_deg");
            plots(table,"AF 02 - Lift coefficient vs elapsed time","elapsed_s","CL");
            plots(table,"AF 03 - Drag coefficient vs elapsed time","elapsed_s","CD");
            plots(table,"AF 04 - Hinge moment vs elapsed time","elapsed_s","Mh_Nm_per_m");
            plots(table,"AF 05 - Flap pressure vs elapsed time","elapsed_s","flap_pabs_kPa","vapor_pressure_kPa");
            plots(table,"AF 06 - Lift coefficient vs flap deflection","measured_deg","CL");
            plots(table,"AF 07 - Drag coefficient vs flap deflection","measured_deg","CD");
            XYPlot check=(XYPlot)sim.getPlotManager().getPlot("AF 02 - Lift coefficient vs elapsed time");
            check.encode(out.resolve("native_plot_lift_preview.png").toString(),"png",1120,620);
            if(sim.getSolution().getPhysicalTime()!=initial)throw new IllegalStateException("Post-processing advanced physical time");
            Path finalFile=Paths.get(System.getenv("FLAP_POST_OUTPUT"));
            if(Files.exists(finalFile))throw new IllegalStateException("Output would overwrite an existing case");
            sim.saveState(finalFile.toString());
            Files.writeString(out.resolve("RECEIPT.json"),"{\"time_s\":"+initial+",\"history_samples\":"+table.getRowCount()+",\"solver_steps\":0,\"added_scenes\":3,\"added_plots\":7}");
        } catch(Exception e){throw new RuntimeException(e);}
    }
}

