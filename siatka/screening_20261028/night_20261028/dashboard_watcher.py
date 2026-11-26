from pathlib import Path
import importlib,time
import update_dashboard
root=Path(r'F:\ntnu\mesh_screening_20261028')
end=time.time()+14*3600
while time.time()<end:
 try:
  importlib.reload(update_dashboard)
  update_dashboard.build(root)
  (root/'night_20261028/dashboard_heartbeat.txt').write_text(str(time.time()))
 except Exception as error:print('Dashboard refresh deferred',type(error).__name__,flush=True)
 if (root/'night_20261028/STOP_DASHBOARD').exists():break
 time.sleep(30)
