from pathlib import Path
h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102')
p=h/'macros/StabilizeHydro.java';t=p.read_text(encoding='utf8')
needle='note("URANS stabilization; minimum 500 and maximum 2000 physical steps");'
insert='''StringBuilder schedule=new StringBuilder();for(Monitor mon:s.getMonitorManager().getObjects())if(mon instanceof ReportMonitor){schedule.append(mon.getPresentationName()+" before_enabled="+mon.getEnabled()+" before_trigger="+mon.getTriggerOption().getSelected()+"\\n");if(mon.getPresentationName().startsWith("HF_")){mon.getTriggerOption().setSelected(MonitorTriggerOption.TIME_STEP);mon.getStarUpdate().setUpdateMode(StarUpdate.TIMESTEP);mon.getStarUpdate().setUpdateFrequency(1);}else mon.setEnabled(false);}Files.writeString(out.resolve("monitor_schedule.txt"),schedule.toString());\n'''
assert needle in t;t=t.replace(needle,insert+needle);p.write_text(t,encoding='utf8')
p=h/'macros/BuildExtrudedHydroMesh.java';t=p.read_text(encoding='utf8')
needle='if(over){IndirectRegionInterface'
insert='''int orientationBefore=s.get(MeshManager.class).checkFaceOrientation(regions);s.get(MeshManager.class).repairFaceOrientation(regions);int orientationAfter=s.get(MeshManager.class).checkFaceOrientation(regions);Files.writeString(out.resolve("face_orientation_fixed.txt"),"Before="+orientationBefore+" After="+orientationAfter+"\\n");if(orientationAfter!=0)throw new IllegalStateException("Orientation correction incomplete");
'''
assert needle in t;t=t.replace(needle,insert+needle);p.write_text(t,encoding='utf8')
print('Per-time-step report histories; exact-builder includes verified native face orientation repair')
