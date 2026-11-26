"""Hold an already-stopped, saved STAR server without solving or timeout-killing it."""
import ctypes,json,os,sys,time
from pathlib import Path
import manual_control_common as c
import manual_control_server as service
import run_until_settled as e
R=c.R;case=c.W/'W01_W20L4_M10_FS020_diagnostic_r1';oldpid=32956;launcher=23564
def main():
 done=c.read(case/'completed.json');lock=R/'queue.lock';own=R/'held_wave_server.lock'
 if done.get('status')!='stopped_by_marker' or done.get('time_s',0)<=0 or not (case/'final.sim').is_file():raise RuntimeError('No completed pause save.')
 if c.read(lock).get('pid')!=oldpid or not service.alive(oldpid) or not service.alive(launcher):raise RuntimeError('Ownership or process changed; inspect instead.')
 ident=c.read(case/'source_identity.json')
 if c.digest(Path(ident['source']))!=ident['source_sha256'] or c.digest(case/'input.sim')!=ident['input_sha256']:raise RuntimeError('Source identity changed.')
 e.write(case/'pause_server_handover.json',dict(at=e.stamp(),old_controller_pid=oldpid,server_launcher_pid=launcher,reason='User requested pause for unplugging power and explicitly keep server open',final_sim=str(case/'final.sim'),completed=done))
 # Terminate only the finished-run supervisor, never its child server or any process tree.
 k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
 h=k.OpenProcess(1,False,oldpid)
 if not h:raise RuntimeError('Cannot replace supervisor.')
 try:
  if not k.TerminateProcess(h,0):raise RuntimeError('Supervisor termination failed.')
 finally:k.CloseHandle(h)
 for _ in range(50):
  if not service.alive(oldpid):break
  time.sleep(.1)
 if service.alive(oldpid):raise RuntimeError('Previous supervisor remains active.')
 for name in ('queue.lock','first_foil_wave_diagnostic_r1.lock'):
  f=R/name
  if c.read(f).get('pid')==oldpid:f.rename(R/(name+'.pause_preserved_'+time.strftime('%Y%m%d_%H%M%S')))
 with lock.open('x') as f:json.dump(dict(pid=os.getpid(),purpose='Saved paused wave server; retained for interactive inspection',case=case.name),f)
 with own.open('x') as f:json.dump(dict(pid=os.getpid(),launcher_pid=launcher),f)
 result=dict(returncode=None,source_unchanged=True,completed=done,server_kept_open=True,computation_active=False,supervisor_replaced_after_completed_save=True)
 e.write(case/'controller_result.json',result)
 try:
  while service.alive(launcher):
   e.write(R/'wave_foil_run_state.json',dict(status='paused_saved_server_open',updated_at=e.stamp(),controller_pid=os.getpid(),launcher_pid=launcher,case=case.name,directory=str(case),gpu=False,workers=0,computation_active=False,server_kept_open=True,progress=done,result=result,scope='W01 paused by user; calculated state saved; server retained for inspection'))
   e.write(R/'queue_state.json',dict(status='paused_saved_server_open',active=case.name,updated_at=e.stamp(),purpose='No steps running; server held open at user request'))
   time.sleep(5)
 finally:
  for f in (own,lock):
   if c.read(f).get('pid')==os.getpid():f.unlink()
  e.write(R/'wave_foil_run_state.json',dict(status='paused_saved_server_closed',updated_at=e.stamp(),controller_pid=os.getpid(),case=case.name,directory=str(case),gpu=False,computation_active=False,server_kept_open=False,result=result,progress=done))
if __name__=='__main__':main()
