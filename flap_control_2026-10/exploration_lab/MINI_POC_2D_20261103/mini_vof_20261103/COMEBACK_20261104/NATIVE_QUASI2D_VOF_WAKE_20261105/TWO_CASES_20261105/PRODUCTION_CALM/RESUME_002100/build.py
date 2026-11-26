from pathlib import Path
import sys
d=Path(sys.argv[1])
s=(d.parent/"MiniVofStokes.java").read_text(encoding="utf-8-sig")
a='''    h.setAutoRecord(!moving);
    h.setAutoRescan(!moving);
    write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",h.getNumberOfStates(),"auto_record",h.getAutoRecord()));'''
assert s.count(a)==1
s=s.replace(a,'''    int archivedFrames=h.getNumberOfStates();
    h.setAutoRecord(false);
    h.setAutoRescan(false);
    if(b("af_branch_history")){
     RecordedSolutionView view=null;
     for(var item:s.get(SolutionViewManager.class).getObjects())
      if(item instanceof RecordedSolutionView v&&v.getSolutionHistory().equals(h)&&v.getPresentationName().equals("AF - Playback"))view=v;
     if(view==null)throw new IllegalStateException("AF playback view missing");
     Path fresh=out.resolve(out.getFileName()+"_AF_resume.simh");
     SolutionHistory next=s.get(SolutionHistoryManager.class).createForFile(fresh.toString(),false);
     next.setAutoRecord(false);next.setAutoRescan(false);
     next.getRegions().setObjects(reg);next.getInputs().setObjects(h.getInputs().getObjects());
     next.setFunctions(h.getFunctions());
     next.createSnapshot(String.format(Locale.ROOT,"AF_resume_t%.6f",s.getSolution().getPhysicalTime()));
     Representation previousRep=view.getRepresentation();
     h.setPresentationName("Archived AF history "+out.getFileName());
     next.setPresentationName("AF - Solution History");
     view.setSolutionHistory(next);view.setStateIndex(next.getMinStateIndex());
     Representation nextRep=view.getRepresentation();
     for(Scene scene:s.getSceneManager().getScenes())
      if(scene.getPresentationName().startsWith("AF FIXED "))
       for(var pd:scene.getDisplayerManager().getObjects())
        if(previousRep.equals(pd.getRepresentation()))pd.setRepresentation(nextRep);
     next.getStarUpdateStageable().getStarUpdate().setUpdateMode(StarUpdate.TIMESTEP);
     next.getStarUpdateStageable().getStarUpdate().setUpdateFrequency(25);
     next.setAutoRecord(true);
     write("AF_RESUME_HISTORY.json",Map.of("path",fresh.toString(),"archive_path",local.toString(),"archived_frames",archivedFrames,
      "states_before_solve",next.getNumberOfStates(),"auto_record",next.getAutoRecord(),"auto_rescan",next.getAutoRescan()));
    }else{
     write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",archivedFrames,"auto_record",false));
    }''')
s=s.replace('if(seedSize<window||seedSize>=2*window','if(seedSize<1||seedSize>=2*window')
s=s.replace('if(n>=(fixedHistorySeeded?2:4)*w&&n%w==0){','if(n>=2*w&&n%w==0&&i("fixed_elapsed_before",0)+step>=4*w){')
a='''     for(SolutionHistory history:s.get(SolutionHistoryManager.class).getObjects())
      if(history.getPresentationName().startsWith("AF - "))historyCounts.put(history.getPresentationName(),history.getNumberOfStates());'''
assert s.count(a)==1
s=s.replace(a,'''     for(SolutionHistory history:s.get(SolutionHistoryManager.class).getObjects()){
      if(history.getPresentationName().equals("AF - Solution History")&&b("af_branch_history"))history.rescanFile();
      if(history.getPresentationName().startsWith("AF - "))historyCounts.put(history.getPresentationName(),history.getNumberOfStates());
     }''')
(d/"MiniVofStokes.java").write_text(s,encoding="utf-8")

