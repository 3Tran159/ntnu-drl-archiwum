from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
p=h/'macros/RepairExtrudedMesh.java';t=p.read_text(encoding='utf8')
t=t.replace('getDirection().setComponents(0,.02,0)','getDirection().setComponents(0,-.02,0)')
t=t.replace('exactly +0.02 m in y','outward -0.02 m in y, then restoring original span interval')
t=t.replace('note("Generating one extruded span layer");ve.execute();','note("Generating one extruded span layer");ve.execute();\ns.getRepresentationManager().translateMesh(new Vector<Region>(List.of(fresh)),new Vector<Double>(List.of(0.,.02,0.)),s.getUnitsManager().getObject("m"),s.getCoordinateSystemManager().getLabCoordinateSystem());')
t=t.replace('direction_m\\\":[0,0.02,0]','direction_m\\\":[0,-0.02,0],\\\"post_extrusion_translation_m\\\":[0,0.02,0]')
p.write_text(t,encoding='utf8')
p=h/'tools/native_launch.py';t=p.read_text(encoding='utf8')
t=t.replace("'StabilizeHydro.java'}","'StabilizeHydro.java','BuildExtrudedHydroMesh.java'}",1)
old=" else:\n  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'"
new=""" elif macro.name in {'RepairExtrudedMesh.java','BuildExtrudedHydroMesh.java'} and variant in {'SP_B','SP_C'}:
  receipt=json.loads((R/'audit/launch_StabilizeHydro.json').read_text())
  assert receipt['pid']==owned[0]['ProcessId'] and receipt['variant']=='SP_A' and receipt['executed_macro'] in owned[0]['CommandLine'],'Only independent mesh alongside SP_A stabilization'
  reason='Independent owned SP_A convergence (8 CPU) and flap mesh (4 CPU), no shared outputs'
 else:
  assert macro.name=='InitializeHydroControl.java' and variant=='SP_A','Owned hydro process already active'"""
assert old in t
t=t.replace(old,new);p.write_text(t,encoding='utf8')
print('Outward extrusion + native region translation; bounded independent overlap registered')
