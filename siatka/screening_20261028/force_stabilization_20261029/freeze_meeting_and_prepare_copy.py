from pathlib import Path
import json,datetime
R=Path(__file__).resolve().parent;B=R.parent
import manual_control_common as c
# Freeze after the read-only monitor has stopped; never kill the STAR server.
import manual_control_server as s
if s.alive(1972):raise RuntimeError('Dashboard writer still running; wait for its graceful exit.')
v=dict(at=datetime.datetime.now().astimezone().isoformat(),reason='User taking both current dashboards to meeting; all further edits in copies',sha256={n:c.digest(B/n) for n in ('dashboard.html','professor_dashboard.html')})
f=R/'meeting_dashboard_freeze_20261030.json'
if f.exists():raise RuntimeError('Freeze record already exists; preserve it.')
f.write_text(json.dumps(v,indent=2),encoding='utf8')
src=(R/'collect_computer_status.py').read_text(encoding='utf8')
src=src.replace("'computer_status.json'","'control_computer_status.json'")
src=src.replace("out['activity']={'state':'running'","out['activity']={'state':('paused' if s.get('computation_active') is False else 'running')")
(R/'collect_control_status.py').write_text(src,encoding='utf8')
print('Original meeting files frozen; copy-only telemetry prepared.')
