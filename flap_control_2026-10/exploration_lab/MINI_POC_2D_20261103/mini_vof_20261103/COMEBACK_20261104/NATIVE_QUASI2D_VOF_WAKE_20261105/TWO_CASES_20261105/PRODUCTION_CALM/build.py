from pathlib import Path
import sys
d=Path(sys.argv[1])
p=Path(sys.argv[2])
s=(p/"MiniVofStokes.java").read_text(encoding="utf-8-sig")
a='   new AfNativeOutput().install(s,reg,walls,flaps,out,moving);'
assert s.count(a)==1
s=s.replace(a,'''   String previousHistory=cfg.getProperty("source_af_history","");
   if(!previousHistory.isBlank()){
    Path src=Paths.get(previousHistory);
    if(!Files.isRegularFile(src)||!src.getFileName().toString().endsWith(".simh"))throw new IllegalStateException("AF restart history missing");
    SolutionHistory h=s.get(SolutionHistoryManager.class).getSolutionHistory("AF - Solution History");
    Path local=out.resolve(h.getPath().toPath()).normalize();
    if(!local.getParent().equals(out.normalize())||!local.getFileName().equals(src.getFileName()))
     throw new IllegalStateException("AF history would write outside the owned run: "+local);
    Files.copy(src,local);
    h.rescanFile();
    if(h.getNumberOfStates()<1)throw new IllegalStateException("AF restart history did not load");
    h.setAutoRecord(!moving);
    h.setAutoRescan(!moving);
    write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",h.getNumberOfStates(),"auto_record",h.getAutoRecord()));
   }
   new AfNativeOutput().install(s,reg,walls,flaps,out,moving,!previousHistory.isBlank());
''')
s=s.replace("Path folder, boolean moving) throws Exception {","Path folder, boolean moving, boolean keepHistory) throws Exception {")
s=s.replace('    }else history();','    }else if(!keepHistory)history();')
(d/"MiniVofStokes.java").write_text(s,encoding="utf-8")

