from pathlib import Path
h=Path(__file__).resolve().parents[1]
p=h/'tools/native_launch.py';t=p.read_text(encoding='utf8')
old=" elif macro.name=='StabilizeHydro.java' and variant=='SP_A':"
new=""" elif macro.name=='RunHydroStatic.java' and variant=='SP_B':
  receipt=json.loads((R/'audit/launch_CheckHydroMotion.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['executed_macro'] in owned[0]['CommandLine'],'Only SP_B control alongside independent SP_C motion check'
  reason='Validated stationary SP_B mesh: initialize and stabilize; independent SP_C motion-only test uses one rank'
 elif macro.name=='StabilizeHydro.java' and variant=='SP_A':"""
assert old in t;t=t.replace(old,new);p.write_text(t,encoding='utf8')
p=h/'macros/RunHydroStatic.java';t=p.read_text(encoding='utf8')
needle='if(!input.startsWith(root.resolve("cases")))throw new IllegalStateException("Working case only");'
repl=needle+'String name=input.getFileName().toString();if(!((variant.equals("SP_B")&&name.equals("SP_B_mesh_ready.sim"))||(variant.equals("SP_C")&&(name.equals("motion_verified.sim")||name.equals("pose_ready.sim")))))throw new IllegalStateException("Initialization pipeline only for newly prepared model/pose, never an existing flow checkpoint");'
assert needle in t;t=t.replace(needle,repl);p.write_text(t,encoding='utf8')
print('New-control-only pipeline guard; separate motion-only overlap')
