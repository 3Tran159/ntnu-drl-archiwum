from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'tools/native_launch.py';t=p.read_text(encoding='utf8')
needle=" elif macro.name=='RunHydroStatic.java' and variant=='SP_B':"
insert=""" elif macro.name=='InitializeHydroControl.java' and variant=='SP_C':
  receipt=json.loads((R/'audit/launch_RunHydroStatic.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_B' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_C initialization alongside SP_B control'
  assert sim.name=='motion_verified.sim' and json.loads((sim.parent/'motion_status.json').read_text())['mechanics_passed'],'Overset movement proof required'
  reason='SP_C initialization on 2 CPU after full motion proof; independent SP_B stabilization on 8 CPU'
"""
assert needle in t;t=t.replace(needle,insert+needle)
t=t.replace("else 65 if macro.name in", "else 65 if (macro.name=='InitializeHydroControl.java' and variant=='SP_C') else 65 if macro.name in")
needle="args.extend(['-np',str(np),'-mpi','ms','-cpubind','off'])"
t=t.replace(needle,"if owned and macro.name=='InitializeHydroControl.java' and variant=='SP_C':np=2\n"+needle)
p.write_text(t,encoding='utf8');print('Verified Overset initialization may use 2 CPU alongside 8 CPU fixed control')
