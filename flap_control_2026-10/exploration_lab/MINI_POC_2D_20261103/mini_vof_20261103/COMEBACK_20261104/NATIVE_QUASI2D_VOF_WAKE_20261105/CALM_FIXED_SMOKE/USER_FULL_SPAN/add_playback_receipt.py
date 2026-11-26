from pathlib import Path
import json,os,sys
from hashlib import sha256
d,p=map(Path,sys.argv[1:])
day=json.loads((p/"DAY_STATUS.json").read_text())
run=Path(day["output"])
if day["stage"]!="CALM_VOF_NATIVE_FULL_BAND_FIXED_SMOKE30" or "Playing macro" in (run/"client.log").read_text(errors="replace"):
    raise RuntimeError("The copied macro has already started or the run changed")
s=(d/"MiniVofStokes.java").read_text()
a='   new AfNativeOutput().install(s,reg,walls,flaps,out,moving);'
assert s.count(a)==1
s=s.replace(a,'''   if(b("native_remesh_initialize")){
    for(Scene old:s.getSceneManager().getScenes())
     if(old.getPresentationName().startsWith("AF FIXED"))old.setPresentationName("Previous mesh - "+old.getPresentationName());
   }
'''+a)
a='     "time_s",s.getSolution().getPhysicalTime(),"scenes",List.of("mesh","speed","pressure","streamlines","water","foil")));'
assert s.count(a)==1
s=s.replace(a,a+'''
    try{
     RecordedSolutionView last=null;
     for(var item:s.getSolutionViewManager().getObjects())
      if(item instanceof RecordedSolutionView view&&view.getPresentationName().endsWith(out.getFileName().toString()))last=view;
     if(last==null)throw new IllegalStateException("Final recorded solution view missing");
     last.setStateIndex(h.getMaxStateIndex());
     Map<String,Object> evidence=new LinkedHashMap<>();
     for(Scene sc:s.getSceneManager().getScenes()){
      String name=sc.getPresentationName();
      if(!name.startsWith("AF FIXED")||name.contains("01 -")||name.contains("05 -"))continue;
      String key=name.contains("06 -")?"mesh":name.contains("02 -")?"pressure":name.contains("03 -")?"velocity":"streamlines";
      long assigned=sc.getDisplayerManager().getObjects().stream()
        .filter(displayer->displayer.getRepresentation().equals(lastRepresentation(sc))).count();
      evidence.put(key,Map.of("scene",name,"displayers_on_recorded_view",assigned));
      sc.printAndWait(out.resolve("AF_RECORDED_"+key+".png").toString(),1,1100,650);
     }
     write("AF_PLAYBACK_SCENES.json",evidence);
    }catch(Exception e){write("AF_PLAYBACK_PREVIEW_WARNING.json",Map.of("error",e.toString()));}
''')
s=s.replace('     Map<String,Object> evidence=new LinkedHashMap<>();','     Representation active=last.getRepresentation();\n     Map<String,Object> evidence=new LinkedHashMap<>();')
s=s.replace('displayer.getRepresentation().equals(lastRepresentation(sc))','active.equals(displayer.getRepresentation())')
for f in [d/"MiniVofStokes.java",run/"MiniVofStokes.java"]:
    tmp=f.with_suffix(".pending")
    tmp.write_text(s,encoding="utf-8")
    os.replace(tmp,f)
job=run/"job.json"
j=json.loads(job.read_text())
j["macro_sha256"]=sha256((run/"MiniVofStokes.java").read_bytes()).hexdigest()
tmp=job.with_suffix(".pending")
tmp.write_text(json.dumps(j,indent=2),encoding="utf-8")
os.replace(tmp,job)

