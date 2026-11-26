from pathlib import Path

d=Path(__file__).resolve().parent
s=(d/"MiniVofStokes.java").read_text(encoding="utf8")
s=s.replace('  int window=(int)Math.round(.05/dt), max=(int)Math.round(1./dt), consecutive=0;',
'''  double cap=d("fixed_cap_s",1.);
  int window=(int)Math.round(.05/dt), max=(int)Math.round(cap/dt), consecutive=0;''')
s=s.replace('Math.abs(max*dt-1)>1e-9','Math.abs(max*dt-cap)>1e-9')
(d/"MiniVofStokesExtend.java.txt").write_text(s,encoding="utf8")
s=(d/"run_without_w06_slowdown_stop.py").read_text(encoding="utf8")
s=s.replace('output=D/"NO_W06_STOP_RESULT.json"','output=D/"FIXED_EXTENSION_RESULT.json"')
s=s.replace('old=json.loads((D/"RESULT.json").read_text())','old=json.loads((D/"NO_W06_STOP_RESULT.json").read_text())')
a=s.index('    marker=old["W06"]["stop"]')
b=s.index('    checkpoint=json.loads',a)
s=s[:a]+'''    source=Path(old["checkpoint"])
    if (output.exists() or STOP.exists() or old["status"]!="HOLD_FIXED_NOT_SETTLED" or not old["transport_ok"]
        or status["solver_state"]!="STOPPED" or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_TWO_P_MONITOR_W06"
        or source.parent!=Path(status["output"]) or sha(source)!=old["checkpoint_sha256"]
        or abs(old["state"]["time_s"]-1)>1e-8):
        raise RuntimeError("Sharp sealed stabilization extension preflight blocked")
'''+s[b:]
a=s.index('        archived=D/')
b=s.index('        coex.save(output,dict(status="RUNNING"',a)
s=s[:a]+s[b:]
s=s.replace('D/"NO_W06_STOP_WATCH.csv"','D/"EXTENSION_W06_WATCH.csv"')
s=s.replace('D/"NO_W06_STOP_PREFLIGHT.json"','D/"EXTENSION_PREFLIGHT.json"')
s=s.replace('new_job("MATCHED_FIXED_SHARP_SEALED_TWO_P_MONITOR_W06",dict(','new_job("MATCHED_FIXED_SHARP_SEALED_TWO_P_EXTEND",dict(')
s=s.replace('fixed_protocol=True,seeded_single_phase=True','fixed_protocol=True,fixed_cap_s=1.5,seeded_single_phase=True')
s=s.replace('macro_source=D/"MiniVofStokes.java"','macro_source=D/"MiniVofStokesExtend.java.txt"')
(d/"run_fixed_extension.py").write_text(s,encoding="utf8")

