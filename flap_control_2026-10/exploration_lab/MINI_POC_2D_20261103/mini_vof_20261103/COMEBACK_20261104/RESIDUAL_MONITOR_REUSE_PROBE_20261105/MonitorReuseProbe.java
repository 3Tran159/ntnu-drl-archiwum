package macro;
import java.nio.file.*;
import java.util.*;
import star.base.report.*;
import star.common.*;

public class MonitorReuseProbe extends StarMacro {
 public void execute(){
  Simulation s=getActiveSimulation();
  Path out=Path.of(System.getenv("FLAP_BENCH_DIR"));
  try{
   if(s.getNumberOfGpgpus()!=1)throw new IllegalStateException("GPU probe must stay isolated");
   var counts=new LinkedHashMap<ResidualMonitor,Integer>();
   for(Monitor m:s.getMonitorManager().getObjects()) if(m instanceof ResidualMonitor r)
    counts.put(r,r.getAllYValues().length);
   if(counts.size()!=7)throw new IllegalStateException("Expected seven residual monitors");
   s.getSimulationIterator().getAutoSave().setEnabled(false);
   s.getSimulationIterator().getAutoSave().setAutoSaveBatch(false);
   double origin=s.getSolution().getPhysicalTime();
   var lines=new ArrayList<String>();
   lines.add("step,time_s,monitors,new_samples,duplicate_pre_read_s,solver_s,post_read_s");
   for(int k=1;k<=3;k++){
    long ts=System.nanoTime();
    for(var entry:counts.entrySet())
     if(entry.getKey().getAllYValues().length!=entry.getValue())
      throw new IllegalStateException("Residual samples changed outside solver step");
    double pre=(System.nanoTime()-ts)/1e9;
    ts=System.nanoTime();
    s.getSimulationIterator().step(1);
    double solver=(System.nanoTime()-ts)/1e9;
    double t=s.getSolution().getPhysicalTime();
    if(Math.abs(t-(origin+k*.0002))>1e-9)throw new IllegalStateException("Physical time did not advance as expected");
    int samples=0;
    ts=System.nanoTime();
    for(var entry:counts.entrySet()){
     double[] y=entry.getKey().getAllYValues();
     int n=y.length-entry.getValue();
     if(n<=0||n>20)throw new IllegalStateException("Residual samples do not match one timestep");
     for(int i=y.length-n;i<y.length;i++)if(!Double.isFinite(y[i]))throw new IllegalStateException("Nonfinite residual");
     entry.setValue(y.length);
     samples+=n;
    }
    double post=(System.nanoTime()-ts)/1e9;
    for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ReportMonitor r&&m.getPresentationName().startsWith("AF_"))
     r.getAllYValues();
    if(k==2)s.saveState(out.resolve("CHECKPOINT_COPY_ONLY.sim").toString());
    lines.add(k+","+t+","+counts.size()+","+samples+","+pre+","+solver+","+post);
    Files.write(out.resolve("REUSE.csv"),lines);
   }
   Files.writeString(out.resolve("PASS.txt"),"3 physical steps; exact cached residual lengths confirmed after AF reads and a checkpoint save.\n");
  }catch(Exception e){throw new RuntimeException(e);}
 }
}
