"""Adopt only the already-running r2 CPU pilot after its status writer exited. Never launches STAR."""
import os,sys,json,time,ctypes,subprocess,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;W=Path('E:/ntnu/quasi2d_waves_20261029');C=W/'W20_H24_X4_CPUprop_dt1ms_r2'
sys.path.insert(0,str(R));import run_until_settled as e
lock=W/'preparation.lock';PID=36304
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.restype=ctypes.c_void_p
kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
def alive():
 h=kernel.OpenProcess(0x1000,False,PID)
 if not h:return False
 code=ctypes.c_ulong();ok=kernel.GetExitCodeProcess(h,ctypes.byref(code));kernel.CloseHandle(h)
 return bool(ok and code.value==259)
def write(p,obj):
 temp=p.with_name(p.name+'.adopt.'+str(os.getpid())+'.tmp')
 temp.write_text(json.dumps(obj,indent=2),encoding='utf-8')
 for n in range(50):
  try:temp.replace(p);return
  except PermissionError:time.sleep(.1)
 # Retain the complete temp file, and continue monitoring the active solver.
 with (C/'adoption_status_io_errors.log').open('a') as f:f.write(e.stamp()+' '+str(p)+'\n')
def state(status,**kw):
 obj=dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),case=C.name,directory=str(C),workers=2,gpu=False,
 scope='No-foil short propagation pilot; not force or final propagation validation',adopted_launcher_pid=PID,
 original_controller_pid=1852,controller_recovery='Status-file sharing error; existing solver adopted without restart',**kw)
 for p in [R/'wave_propagation_state.json',R/'wave_preparation_state.json']:write(p,obj)
def main():
 info=e.read(C/'process.json',{});assert info.get('launcher_pid')==PID and info.get('workers')==2 and not info.get('gpu')
 assert not lock.exists(),'CPU preparation already owned'
 assert alive(),'Existing launcher is no longer active; inspect completed state'
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),case=C.name,purpose='Adopt existing CPU pilot',launcher_pid=PID),f)
 write(C/'adoption.json',dict(at=e.stamp(),pid=os.getpid(),launcher_pid=PID,reason='Original controller exited on status-file atomic replace access error; CFD history kept advancing'))
 start=datetime.datetime.fromisoformat(info['started_at']).timestamp()
 try:
  while alive():
   elapsed=time.time()-start;progress=e.read(C/'progress.json',{})
   age=time.time()-(C/'history.csv').stat().st_mtime
   reason=None
   if e.free_memory()<12*1024**3:reason='resource_guard'
   if (R/'STOP_ALL').exists():reason='user_stop'
   if elapsed>2900:reason='controller_wall_budget'
   if age>180:reason='no_history_progress'
   if reason:
    (C/'STOP').write_text(reason,encoding='utf-8')
    state('saving_partial_pilot',reason=reason,progress=progress,elapsed_s=elapsed)
   else:state('propagation_CPU_running',progress=progress,elapsed_s=elapsed,history_age_s=age)
   if elapsed>3300:
    # Exact recorded process only; launcher has remained continuously alive since adoption.
    subprocess.run(['taskkill','/PID',str(PID),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    state('needs_review',reason='Owned adopted launcher exceeded save grace; preserved checkpoint',progress=progress);return
   time.sleep(15)
  done=e.read(C/'completed.json',{});identity=e.read(C/'source_identity.json',{})
  unchanged=e.digest(Path(identity['source']))==identity['source_sha256'] and e.digest(C/'input.sim')==identity['copied_sha256']
  result=dict(completed=done,source_unchanged=unchanged,adopted=True,elapsed_s=time.time()-start,final_exists=(C/'final.sim').exists(),note='Original stdout pipe ended with controller; independent CSV and macro completion are authoritative')
  write(C/'controller_result_adopted.json',result)
  good=unchanged and result['final_exists'] and done.get('status')=='target_reached' and done.get('steps')==1000
  state('propagation_pilot_complete_pending_review' if good else 'partial_pilot_saved_needs_continuation',result=result)
 finally:
  if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
