from pathlib import Path
import sys
d=Path(sys.argv[1])
s=(d.parent/"MiniVofStokes.java").read_text(encoding="utf-8-sig")
anchor='    if(moving) {\n      ((ExpressionReport)monitors'
assert s.count(anchor)==1
s=s.replace(anchor,'''    for(SolutionHistory previous:s.get(SolutionHistoryManager.class).getObjects()){
      if(previous.getPresentationName().startsWith("AF - Fixed VOF Solution History")){
        previous.setAutoRecord(false);
        previous.setAutoRescan(false);
      }
    }
'''+anchor)
s=s.replace('''      for(SolutionHistory h:s.get(SolutionHistoryManager.class).getObjects())
        if(h.getPresentationName().equals("AF - Fixed VOF Solution History"))h.setAutoRecord(false);
''','')
s=s.replace('h.setPresentationName("AF - Fixed VOF Solution History");','h.setPresentationName("AF - Fixed VOF Solution History " + out.getFileName());')
s=s.replace('view.setPresentationName("AF - Fixed VOF playback");','view.setPresentationName("AF - Fixed VOF playback " + out.getFileName());')
s=s.replace('if(b("af_native")&&(step==1||step==25))','if(b("af_native")&&(step==1||step%25==0))')
(d/"MiniVofStokes.java").write_text(s,encoding="utf-8")

