package macro;

import java.nio.file.*;
import star.common.*;
import star.vis.*;

public class VerifyFlapArchive extends StarMacro {
    void label(Axis axis,String text){
        if(axis==null)throw new IllegalStateException("Plot axis missing");
        AxisTitle title=axis.getTitle();
        title.setAutoUpdate(false);
        title.setText(text);
        title.setTextLocked(true);
    }
    String yLabel(String x){
        return switch(x){
            case "measured_deg","command_deg" -> "Flap deflection [deg]";
            case "CL" -> "Lift coefficient, CL";
            case "CD" -> "Drag coefficient, CD";
            case "Mh_Nm_per_m" -> "Hinge moment [N m/m]";
            case "flap_pabs_kPa","vapor_pressure_kPa" -> "Absolute pressure [kPa]";
            default -> x;
        };
    }
    public void execute(){
        Simulation s=getActiveSimulation();
        try{
            Path dir=Paths.get(System.getenv("FLAP_POST_DIR"));
            double t=s.getSolution().getPhysicalTime();
            if(Math.abs(t-Double.parseDouble(System.getenv("FLAP_POST_TIME")))>1e-9||s.getNumberOfGpgpus()!=0)
                throw new IllegalStateException("Archive physical time or GPU mismatch");
            Table data=s.getTableManager().getTable("AF - Archived transient cycle");
            int n=Integer.parseInt(System.getenv("FLAP_POST_ROWS"));
            if(data==null||data.getRowCount()!=n)throw new IllegalStateException("Archived plot history missing");
            int plots=0;
            for(StarPlot p:s.getPlotManager().getPlots())if(p.getPresentationName().startsWith("AF ")){
                plots++;
                int series=0;
                for(var item:p.getDataSetManager().getExternalDataSets()){
                    ExternalDataSet ds=(ExternalDataSet)item;
                    if(ds.getTable()==null||ds.getTable().getRowCount()!=n)throw new IllegalStateException("Plot table data missing");
                    label(ds.getXAxis(),ds.getXValuesName().equals("elapsed_s")?"Time since motion onset [s]":"Measured flap deflection [deg]");
                    label(ds.getYAxis(),yLabel(ds.getYValuesName()));
                    ds.getSymbolStyle().setSymbolShapeOptionInput(SymbolShapeOption.Type.NONE);
                    ds.getLineStyle().setLinePatternOptionInput(LinePatternOption.Type.SOLID);
                    ds.getLineStyle().setLineWidth(1.8);
                    series++;
                }
                if(series<1)throw new IllegalStateException("Archived plot has no data");
            }
            if(plots!=7)throw new IllegalStateException("Archived plot count is "+plots);
            s.getPlotManager().getPlot("AF 02 - Lift coefficient vs elapsed time").encode(dir.resolve("native_plot_lift_preview.png").toString(),"png",1120,620);
            int scenes=0;
            for(Scene sc:s.getSceneManager().getScenes())if(sc.getPresentationName().startsWith("AF ")){
                scenes++;
                if(sc.getDisplayerManager().getDisplayers().isEmpty())throw new IllegalStateException("Archived scene display missing");
                if(sc.getPresentationName().contains("Absolute pressure")){
                    ScalarDisplayer d=(ScalarDisplayer)sc.getDisplayerManager().getDisplayer("Absolute pressure");
                    d.getScalarDisplayQuantity().setRangeMin(-60000);
                    d.getScalarDisplayQuantity().setRangeMax(200000);
                    sc.printAndWait(dir.resolve("absolute_pressure.png").toString(),1,1450,820);
                }
            }
            if(scenes!=3||s.getSolution().getPhysicalTime()!=t)throw new IllegalStateException("Scene count or physical time mismatch");
            Path output=Paths.get(System.getenv("FLAP_POST_OUTPUT"));
            if(Files.exists(output))throw new IllegalStateException("Verification output exists");
            s.saveState(output.toString());
            Files.writeString(dir.resolve("VERIFY.json"),"{\"reopened\":true,\"time_s\":"+t+",\"solver_steps\":0,\"history_samples\":"+n+",\"scenes\":"+scenes+",\"plots\":"+plots+"}");
        }catch(Exception e){throw new RuntimeException(e);}
    }
}
