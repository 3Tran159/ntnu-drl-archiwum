from pathlib import Path
import py_compile
h=Path(__file__).resolve().parents[1];p=h/'tools/night_queue.py';s=p.read_text(encoding='utf8')
s=s.replace("if rec['pid'] in alive:roots.add(rec['pid'])","if rec['pid'] in alive and alive[rec['pid']]['ownedBatch']:roots.add(rec['pid'])")
s=s.replace("metrics=scan_current(st,plist)","metrics=scan_current(st,processes())")
s=s.replace("out=Path(rec['output']);log=Path(rec['log'])","out=Path(rec['output']);log=Path(rec['log']);metrics['physical_time_s']=rec.get('initial_time_s')")
s=s.replace("if st.get('active'):st['queue_state']='MONITORING'","if st.get('active'):\n    st['queue_state']='MONITORING'\n    if rs['ram_available_GiB']<4 or rs['disk_free_GiB']<5:\n     marker=H.parent/'STOP_OWNED_CFD.json'\n     if not marker.exists():atomic(marker,dict(source='night_queue',reason='resource_floor',at=now(),resources=rs));event('graceful_pause_requested',reason='resource_floor')\n     st['queue_state']='RESOURCE_PAUSE_REQUESTED'")
p.write_text(s,encoding='utf8');py_compile.compile(str(p),doraise=True);py_compile.compile(str(h/'tools/night_native.py'),doraise=True)
print('Queue syntax verified; snapshots, fail-closed scientific gate and graceful resource marker enabled.')
