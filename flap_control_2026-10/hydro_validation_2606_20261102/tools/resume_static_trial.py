from pathlib import Path
import json,subprocess,sys
h=Path(__file__).resolve().parents[1]
p=h/'tools/native_launch.py';t=p.read_text(encoding='utf8')
old=" else:\n  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'"
new=""" elif macro.name=='StabilizeHydro.java' and variant=='SP_A':
  receipt=json.loads((R/'audit/launch_BuildExtrudedHydroMesh.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_C' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent SP_A alongside owned SP_C mesh'
  reason='Resume owned SP_A fields while independent SP_C mesh uses 2 ranks'
 else:
  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'"""
assert old in t;t=t.replace(old,new);p.write_text(t,encoding='utf8')
a=h/'cases/SP_A_original_singlephase/stabilize_20261102_190626/stabilize_20261102_191755'
status=json.loads((a/'status.json').read_text());assert status['status']=='paused_by_marker'
marker=h.parent/'STOP_OWNED_CFD.json';assert json.loads(marker.read_text())['not_a_user_pause']
marker.rename(h/'audit/stop_for_static_dt_trial_20261102_1930.json')
print('Checkpoint physical time preserved:',status['saved_time_s'])
subprocess.run([sys.executable,str(p),'StabilizeHydro.java',str(a/'checkpoint.sim'),'SP_A'],check=True)
