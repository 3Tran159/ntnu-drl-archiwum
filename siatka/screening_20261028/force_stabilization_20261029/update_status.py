"""Refresh measured state, English plots and standalone HTML."""
import os,subprocess,sys,time,json
from pathlib import Path
R=Path(__file__).resolve().parent
plotpy=Path(r"E:\Program Files\Siemens\21.02.007-R8\STAR-CCM+21.02.007-R8\star\lib\python\python.exe")
env=dict(os.environ,PYTHONIOENCODING='utf-8')
def run(script,exe=sys.executable,timeout=15):
 p=subprocess.run([str(exe),str(R/script)],capture_output=True,env=env,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 if p.returncode:raise RuntimeError(script+': '+p.stderr.decode('utf-8',errors='replace')[-1200:])
run('collect_status.py')
last=R/'plot_refresh.json'
if not (R/'field_refresh.lock').exists() and (not last.exists() or time.time()-last.stat().st_mtime>75):
 try:
  run('yplus_diagnostic.py',plotpy);run('analyze_forces.py',plotpy)
  wave_state=R/'wave_propagation_state.json'
  if wave_state.exists():
   wave=json.loads(wave_state.read_text(encoding='utf-8-sig'))
   folder=Path(wave.get('directory',''))
   if (folder/'gauges.csv').exists() and (folder/'history.csv').exists():
    run('plot_wave_pilot_live.py',plotpy)
  last.write_text(json.dumps({'updated_unix':time.time()}))
 except Exception as e:(R/'plot_refresh_error.txt').write_text(str(e))
run('build_dashboard_en.py')

run('build_professor_dashboard.py')
