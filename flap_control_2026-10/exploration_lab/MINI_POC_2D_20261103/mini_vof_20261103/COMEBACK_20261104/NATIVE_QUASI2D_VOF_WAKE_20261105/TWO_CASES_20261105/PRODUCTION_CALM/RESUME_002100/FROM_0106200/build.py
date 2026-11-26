from pathlib import Path
import sys
d=Path(sys.argv[1])
s=(d.parent/"MiniVofStokes.java").read_text(encoding="utf-8-sig")
a='''    }else{
     write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",archivedFrames,"auto_record",false));
    }'''
assert s.count(a)==1
s=s.replace(a,'''    }else{
     h.setAutoRecord(!moving);
     if(!moving){
      for(var item:s.get(SolutionViewManager.class).getObjects())
       if(item instanceof RecordedSolutionView v&&v.getPresentationName().equals("AF - Playback")&&v.getSolutionHistory().equals(h))
        v.setStateIndex(h.getMaxStateIndex());
     }
     write("AF_RESUME_HISTORY.json",Map.of("path",local.toString(),"states_before_solve",archivedFrames,"auto_record",h.getAutoRecord()));
    }''')
s=s.replace('&&b("af_branch_history"))history.rescanFile();','&&!cfg.getProperty("source_af_history","").isBlank()&&!moving)history.rescanFile();')
a='double saveInterval=d("save_interval_s",T),nextSave=start+saveInterval;'
assert s.count(a)==1
s=s.replace(a,'double saveInterval=d("save_interval_s",T),earlySave=d("early_save_interval_s",saveInterval),nextSave=start+earlySave;')
a='nextSave+=saveInterval;'
assert s.count(a)==1
s=s.replace(a,'nextSave+=step<i("early_save_steps",0)?earlySave:saveInterval;')
(d/"MiniVofStokes.java").write_text(s,encoding="utf-8")
s=(d.parent/"resume.py").read_text(encoding="utf-8-sig")
s=s.replace("P=D.parents[3]","P=D.parents[4]")
s=s.replace('START=P/"runs"/(FIXED+"_20261105_140934")','''START=P/"runs"/(FIXED+"_20261105_144455")
PREFIX_A=P/"runs"/(FIXED+"_20261105_140934")
PREFIX_B=P/"runs"/(FIXED+"_20261105_142054")''')
s=s.replace("510b683925285244b30d15a41e3e472e359036cb7f1a3ecb69f3c6bb58c3c8c4","e64b8facf3d5fc5fad8fffe0132a962490d2b39edf73f38fba24a494a7b283cb")
s=s.replace("abs(time_s-.021)","abs(time_s-.1062)")
s=s.replace('    rows=saved_rows(START,used,time_s)','''    rows=saved_rows(PREFIX_A,75,.021)+saved_rows(PREFIX_B,425,.106)+saved_rows(START,used,time_s)
    used=len(rows)
    if used!=501:
        raise RuntimeError("Unexpected saved fixed history length")''')
s=s.replace('checkpoint_interval_s=.005,cpu_indices=CPUS','checkpoint_interval_s=.005,initial_checkpoint_interval_s=.002,cpu_indices=CPUS')
s=s.replace('af_branch_history=True,matched_calm_fixed=True','af_branch_history=False,early_save_interval_s=.002,early_save_steps=50,matched_calm_fixed=True')
a='        for attempt in range(2):'
z='        fixed_copy=c.publish(fixed)'
i=s.index(a)
j=s.index(z,i)
s=s[:i]+'''        seed_rows=rows[-(W+used%W):]
        for i,r in enumerate(seed_rows):
            if (not all(math.isfinite(float(r[k])) for k in ("CL","CD")) or
                abs(float(r["time_s"])-(time_s-(len(seed_rows)-1-i)*DT))>1e-9):
                raise RuntimeError("Force seed time mismatch")
        seed=D/"FIXED_SEED.csv"
        with seed.open("x",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=("time_s","CL","CD"),extrasaction="ignore")
            writer.writeheader()
            writer.writerows(seed_rows)
        status(operation="RESUMING_FIXED_WITH_REPAIRED_PLAYBACK",completed_fixed_steps=used,seeded_samples=len(seed_rows))
        fixed=job(FIXED,source=source,expected_time=time_s,source_af_history=source_history.as_posix(),
            af_branch_history=False,early_save_interval_s=.002,early_save_steps=50,
            matched_calm_fixed=True,moving=False,steps=6000-used,fixed_elapsed_before=used,
            fixed_window_seed=seed.as_posix(),fixed_stable_count=stable,limit_seconds=21600)
'''+s[j:]
(d/"resume.py").write_text(s,encoding="utf-8")

