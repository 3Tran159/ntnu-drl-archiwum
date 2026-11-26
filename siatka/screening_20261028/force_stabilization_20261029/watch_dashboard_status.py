"""Read-only dashboard refresher, separate from solver queue and private uploader."""
import ctypes,datetime,importlib,json,os,subprocess,sys,time
from pathlib import Path
import collect_computer_status as telemetry
R=Path(__file__).resolve().parent;lock=R/'dashboard_status_monitor.lock';stop=R/'STOP_DASHBOARD_MONITOR'
def alive(pid):
 h=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
 if not h:return False
 code=ctypes.c_ulong();ctypes.windll.kernel32.GetExitCodeProcess(h,ctypes.byref(code));ctypes.windll.kernel32.CloseHandle(h)
 return code.value==259
def main():
 if lock.exists():
  previous=telemetry.read(lock)
  if alive(int(previous.get('pid',0))):raise SystemExit('Existing dashboard monitor; not duplicated')
  lock.rename(R/('dashboard_status_monitor.stale.'+str(time.time_ns())+'.json'))
 with lock.open('x') as f:json.dump({'pid':os.getpid(),'purpose':'Read-only dashboard telemetry; never starts a solver','started_at':datetime.datetime.now().astimezone().isoformat()},f)
 try:
  previous_science=None
  while not stop.exists():
   start=time.monotonic()
   try:
    importlib.reload(telemetry);telemetry.collect()
    science_paths=[]
    for pattern in ('wave_*.json','configured_*.json','selected_mesh*.json','matched_endpoint*.json','professor_*review.json','STOP_ALL'):science_paths.extend(R.glob(pattern))
    science=tuple(sorted((str(p),p.stat().st_mtime_ns) for p in science_paths))
    if science!=previous_science:
     review=subprocess.run([sys.executable,str(R/'build_professor_dashboard.py')],capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
     if review.returncode:raise RuntimeError('Research dashboard rebuild failed; inspect its source')
     previous_science=science
    p=subprocess.run([sys.executable,str(R/'build_dashboard_en.py')],capture_output=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode:raise RuntimeError('Operational dashboard rebuild failed; inspect its source')
    telemetry.write(R/'dashboard_monitor_state.json',{'status':'running','pid':os.getpid(),'updated_at':datetime.datetime.now().astimezone().isoformat(),'refresh_seconds':20,'last_cycle_s':time.monotonic()-start,'read_only_solver':True})
   except Exception as exc:
    telemetry.write(R/'dashboard_monitor_state.json',{'status':'refresh_error','pid':os.getpid(),'updated_at':datetime.datetime.now().astimezone().isoformat(),'error':str(exc)})
   time.sleep(max(1,20-(time.monotonic()-start)))
 finally:
  if telemetry.read(lock).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
