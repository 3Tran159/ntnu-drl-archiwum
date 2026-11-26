import subprocess,sys,os,json,time
from pathlib import Path
R=Path(__file__).resolve().parent
PY=r'E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\python\python.exe'
env=dict(os.environ,PYTHONIOENCODING='utf-8')
def run(name,exe):
 p=subprocess.run([exe,str(R/name)],capture_output=True,env=env,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
 if p.returncode:raise RuntimeError(name+': '+p.stderr.decode(errors='replace')[-1800:])
run('select_snapshots.py',sys.executable)
lock=R/'field_refresh.lock'
try:
 lock.write_text(str(os.getpid()))
 for name in ['localize_pressure.py','plot_flow_fields.py','yplus_diagnostic.py','analyze_forces.py']:run(name,PY)
 run('collect_status.py',sys.executable)
 run('mesh_convergence.py',sys.executable)
 run('plot_mesh_comparison.py',PY)
 run('audit_mesh_budget_cfl.py',PY)
 run('build_dashboard_en.py',sys.executable)
 (R/'settled_graphics_updated.json').write_text(json.dumps({'updated_unix':time.time(),'snapshots':json.loads((R/'selected_snapshots.json').read_text())},indent=2))
 print('Saved-field figures refreshed at accepted timestamps.')
finally:
 if lock.exists():lock.unlink()
