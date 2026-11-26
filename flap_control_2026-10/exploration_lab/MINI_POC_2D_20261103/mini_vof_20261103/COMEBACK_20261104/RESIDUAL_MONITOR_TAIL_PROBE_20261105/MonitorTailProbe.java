package macro;

import java.nio.file.*;
import java.util.*;
import star.base.report.*;
import star.common.*;

public class MonitorTailProbe extends StarMacro {
 public void execute() {
  Simulation s=getActiveSimulation();
  Path out=Path.of(System.getenv("FLAP_BENCH_DIR"));
  try{
   var lines=new ArrayList<String>();
   lines.add("monitor,full_count,tail_count,tail_exact,x_exact,full_read_s,tail_read_s");
   int count=0;
   for(Monitor m:s.getMonitorManager().getObjects()) if(m instanceof ResidualMonitor r){
    int prior=r.getPlotLimit();
    try{
     MonitorData full=r.getAllSamples();
     double[] y=full.getYValues(),x=full.getXValues();
     if(y.length<64)continue;
     r.setPlotLimit(64);
     MonitorData tail=r.getPlotSamples();
     double[] shortY=tail.getYValues(),shortX=tail.getXValues();
     boolean exact=shortY.length==64&&Arrays.equals(shortY,Arrays.copyOfRange(y,y.length-64,y.length));
     boolean exactX=shortX.length==64&&Arrays.equals(shortX,Arrays.copyOfRange(x,x.length-64,x.length));
     long start=System.nanoTime();
     for(int i=0;i<5;i++)r.getAllYValues();
     double fullSec=(System.nanoTime()-start)*2e-10;
     start=System.nanoTime();
     for(int i=0;i<5;i++)r.getPlotSamples();
     double shortSec=(System.nanoTime()-start)*2e-10;
     lines.add(r.getPresentationName()+","+y.length+","+shortY.length+","+exact+","+exactX+","+fullSec+","+shortSec);
     count++;
    }finally{r.setPlotLimit(prior);}
   }
   if(count<1)throw new IllegalStateException("No populated residual monitors");
   Files.write(out.resolve("RESIDUAL_TAIL.csv"),lines);
   Files.writeString(out.resolve("TIME.txt"),Double.toString(s.getSolution().getPhysicalTime()));
  }catch(Exception e){throw new RuntimeException(e);}
 }
}
