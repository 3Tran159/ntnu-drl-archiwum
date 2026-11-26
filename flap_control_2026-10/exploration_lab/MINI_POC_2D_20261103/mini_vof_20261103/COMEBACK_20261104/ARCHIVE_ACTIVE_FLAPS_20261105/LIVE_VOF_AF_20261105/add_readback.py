from pathlib import Path
import os,sys
a,p=map(Path,sys.argv[1:])
runs=sorted((p/"runs").glob("CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST*"))
run=runs[-1]
for name in ("server.log","client.log"):
    path=run/name
    if path.exists() and "Playing macro" in path.read_text(errors="replace"):
        raise RuntimeError("Started loading macro")
anchor='    if(playbackHistory!=null&&step%25==0)safelyRecordPlayback(step);'
addition='''    if(b("af_native")&&(step==1||step==25)){
     Map<String,Object> samples=new LinkedHashMap<>();
     for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ReportMonitor rm&&m.getPresentationName().startsWith("AF_")){
      double[] values=rm.getAllYValues();
      samples.put(m.getPresentationName(),Map.of("count",values.length,"last",values.length==0?Double.NaN:values[values.length-1]));
     }
     Map<String,Object> historyCounts=new LinkedHashMap<>();
     for(SolutionHistory history:s.get(SolutionHistoryManager.class).getObjects())
      if(history.getPresentationName().startsWith("AF - "))historyCounts.put(history.getPresentationName(),history.getNumberOfStates());
     write("AF_NATIVE_SAMPLES.json",Map.of("time_s",t,"step",step,"monitors",samples,"history_states",historyCounts,
       "report_CL",cl,"report_CD",cd,"actual_flap_deg",actual));
     if(step==1)save("AF_FIRST_STEP");
    }
'''
src=a/"MiniVofStokes.java"
text=src.read_text()
assert text.count(anchor)==1
text=text.replace(anchor,anchor+"\n"+addition)
for target in [src,run/"MiniVofStokes.java"]:
    tmp=target.with_suffix(".pending")
    tmp.write_text(text,encoding="utf-8")
    os.replace(tmp,target)
print(run)

