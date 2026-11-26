from pathlib import Path
import json,os,sys
d,p=map(Path,sys.argv[1:])
day=json.loads((p/"DAY_STATUS.json").read_text(encoding="utf-8-sig"))
run=Path(day["output"])
if day["stage"]!="CALM_VOF_NATIVE_FULL_BAND_FIXED_SMOKE30" or "Playing macro" in (run/"client.log").read_text(errors="replace"):
    raise RuntimeError("The copied macro has already started or the run changed")
s=(d/"MiniVofStokes.java").read_text()
a='  playbackWalls(playbackScene("AF VOF 01 - Recorded foil geometry"));'
assert s.count(a)==1
s=s.replace(a,a+'''
  Scene meshScene=playbackScene("AF VOF 06 - Recorded mesh");
  PartDisplayer cells=meshScene.getDisplayerManager().createPartDisplayer("Recorded cross-section mesh");
  cells.getInputParts().setObjects(plane);cells.setRepresentation(playbackView.getRepresentation());
  cells.setMesh(true);cells.setOutline(true);playbackWalls(meshScene);
''')
a='    scene("AF FIXED 01 - Recorded foil geometry",rep,.36);'
assert s.count(a)==1
s=s.replace(a,a+'''
    Scene meshScene=scene("AF FIXED 06 - Recorded mesh",rep,.45);
    PartDisplayer cells=meshScene.getDisplayerManager().createPartDisplayer("Recorded cross-section mesh");
    cells.getInputParts().setObjects(plane);cells.setRepresentation(rep);cells.setMesh(true);cells.setOutline(true);
''')
a='  if(playbackHistory!=null)safelyRecordPlayback(done);'
assert s.count(a)==1
s=s.replace(a,a+'''
  if(b("native_remesh_initialize")){
   for(SolutionHistory h:s.get(SolutionHistoryManager.class).getObjects()){
    if(!h.getPresentationName().endsWith(out.getFileName().toString()))continue;
    h.createSnapshot(String.format(Locale.ROOT,"AF_fixed_final_%05d",done));
    write("AF_PLAYBACK_FINAL.json",Map.of("states",h.getNumberOfStates(),"history_file",h.getPath().toString(),
     "time_s",s.getSolution().getPhysicalTime(),"scenes",List.of("mesh","speed","pressure","streamlines","water","foil")));
   }
  }
''')
for f in [d/"MiniVofStokes.java",run/"MiniVofStokes.java"]:
    tmp=f.with_suffix(".pending")
    tmp.write_text(s,encoding="utf-8")
    os.replace(tmp,f)
job=run/"job.json"
j=json.loads(job.read_text())
from hashlib import sha256
j["macro_sha256"]=sha256((run/"MiniVofStokes.java").read_bytes()).hexdigest()
tmp=job.with_suffix(".pending")
tmp.write_text(json.dumps(j,indent=2),encoding="utf-8")
os.replace(tmp,job)
print(run)

