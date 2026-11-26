from pathlib import Path

d=Path(__file__).resolve().parent
out=d/"matched_gap"
out.mkdir(exist_ok=False)
s=(d/"MiniVofStokesExtend.java.txt").read_text(encoding="utf8")
s=s.replace('if(n%((restored?1:4)*window)==0)save','if(n%window==0)save',1)
s=s.replace('      save("FIXED_STABLE");','      exportGapYplus(n);\n      save("FIXED_STABLE");',1)
old='''    Map<ResidualMonitor,Integer> before=new LinkedHashMap<>();
    for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r)before.put(r,r.getAllYValues().length);
'''
assert s.count(old)==1
s=s.replace(old,"",1)
old='''   int total=b("fixed_protocol")?(int)Math.round(.2/dt):i("steps",40);for(int step=1;step<=total;step++){'''
new='''   Map<ResidualMonitor,Integer> before=new LinkedHashMap<>();
   for(Monitor m:s.getMonitorManager().getObjects())if(m instanceof ResidualMonitor r)before.put(r,r.getAllYValues().length);
   int total=b("fixed_protocol")?(int)Math.round(.2/dt):i("steps",40);for(int step=1;step<=total;step++){'''
assert s.count(old)==1
s=s.replace(old,new,1)
s=s.replace('     int n=y.length-entry.getValue();','     int n=y.length-entry.getValue();\n     entry.setValue(y.length);',1)
old='''     result="HOLD_SINGLE_PHASE_SAFETY";break;
    }
   }'''
new='''     result="HOLD_SINGLE_PHASE_SAFETY";break;
    }
    if(step%200==0&&step<total)save(String.format(Locale.ROOT,"ACTIVE_STEP%04d",step));
   }'''
assert s.count(old)==1
(out/"MiniVofStokes.java").write_text(s.replace(old,new,1),encoding="utf8")

