"""Resume only the verified live saved W01 server. No second GPU solver."""
import ctypes,csv,datetime,json,os,shutil,subprocess,threading,time
from pathlib import Path
import run_until_settled as e
import manual_control_common as c
from manual_control_server import alive
from wave_cycle_repeatability import evaluate
R=c.R;W=c.W;case=W/'W01_W20L4_M10_FS020_cycles_r2';source=W/'W01_W20L4_M10_FS020_diagnostic_r1'/'final.sim'
old_holder=28140;server_launcher=23564;server_pid=36856;port=47829
lock=R/'queue.lock';own=R/'wave_cycle_continuation_r2.lock'
def state(status,**kw):
 e.write(R/'wave_foil_run_state.json',dict(status=status,updated_at=e.stamp(),controller_pid=os.getpid(),launcher_pid=server_launcher,server_pid=server_pid,case=case.name,directory=str(case),gpu=True,workers=1,scope='W01 H0.5/L20/depth24 M10; saved-state continuation from0.168s; assess10 cycles, diagnostic cap20',user_mass_exception=True,formal_wave_force_acceptance=False,**kw))
def main():
 audit=e.read(R/'live_w01_resume_audit.json',{});plan=e.read(R/'wave_cycle_continuation_plan_r2.json',{})
 if case.exists() or own.exists():raise RuntimeError('Attempt already exists. Never repeat it.')
 if e.read(lock,{}).get('pid')!=old_holder or not alive(old_holder) or not alive(server_launcher) or not alive(server_pid):raise RuntimeError('Held server ownership changed.')
 if audit.get('status')!='live_saved_W01_identity_passed' or abs(audit.get('time_s',0)-.168)>1e-9:raise RuntimeError('Live audit not passed.')
 if (R/'STOP_ALL').exists() or (W/'preparation.lock').exists():raise RuntimeError('Stop/preparation lock present.')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<30*1024**3:raise RuntimeError('Insufficient resources.')
 auth=e.read(R/'wave_resume_authorization_20261030.json',{})
 if auth.get('status')!='explicit_user_resume_after_meeting':raise RuntimeError('Resume authorization missing.')
 with own.open('x') as f:json.dump(dict(pid=os.getpid(),case=case.name),f)
 p=None;claimed=False
 try:
  case.mkdir();sha=e.digest(source);shutil.copy2(source,case/'source_saved_t0.168.sim');shutil.copy2(R/'W01ResumeCyclesR2.java',case/'W01ResumeCyclesR2.java')
  if e.digest(case/'source_saved_t0.168.sim')!=sha:raise RuntimeError('Checkpoint copy identity failed.')
  e.write(case/'source_identity.json',dict(source=str(source),source_sha256=sha,input_sha256=sha,source_time_s=.168,source_cells=317277,source_is_guard_failed=False,live_server_pid=server_pid,live_server_port=port,reinitialized=False))
  shutil.copy2(R/'wave_resume_authorization_20261030.json',case/'authorization.json');shutil.copy2(R/'wave_cycle_continuation_plan_r2.json',case/'plan.json')
  # Replace only the passive holder, never its STAR server. Root lock is atomically transferred with no unlocked gap.
  k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.CloseHandle.argtypes=[ctypes.c_void_p]
  h=k.OpenProcess(1,False,old_holder)
  if not h:raise RuntimeError('Cannot take over passive holder.')
  try:
   if not k.TerminateProcess(h,0):raise RuntimeError('Holder handover failed.')
  finally:k.CloseHandle(h)
  for _ in range(50):
   if not alive(old_holder):break
   time.sleep(.1)
  if alive(old_holder):raise RuntimeError('Previous holder still active.')
  shutil.copy2(lock,case/'previous_queue_owner.json')
  e.write(lock,dict(pid=os.getpid(),case=case.name,purpose='W01 live server continuation, max20 wave periods'));claimed=True
  hlock=R/'held_wave_server.lock'
  if e.read(hlock,{}).get('pid')==old_holder:hlock.rename(R/('held_wave_server.completed_'+str(int(time.time()))+'.json'))
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
  started=time.time();last_pt=.168;last_progress=started;last_analysis=0;last_status=0;stop_reason=None
  state('wave_continuation_connecting',progress={'time_s':.168},computation_active=True,period_s=plan['period_s'],cycle_target_min=10,cycle_cap=20)
  with (case/'client.log').open('x',encoding='utf8') as log:
   p=subprocess.Popen([str(e.STAR),'-host','127.0.0.1:'+str(port),'-noexit','-batch',str(case/'W01ResumeCyclesR2.java')],cwd=str(case),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
   e.write(case/'process.json',dict(client_pid=p.pid,server_pid=server_pid,server_launcher_pid=server_launcher,started_at=e.stamp(),attached_existing_server=True))
   def drain():
    for line in p.stdout:
     try:log.write(e.redact(line));log.flush()
     except ValueError:break
   th=threading.Thread(target=drain,daemon=True);th.start()
   while p.poll() is None:
    now=time.time();elapsed=now-started;progress=e.read(case/'progress.json',{});pt=progress.get('time_s',.168)
    if pt>last_pt:last_pt=pt;last_progress=now
    memory=e.free_memory();space=shutil.disk_usage(W).free
    if (pt<=.168 and elapsed>900) or (pt>.168 and now-last_progress>600) or memory<8*1024**3 or space<8*1024**3 or elapsed>51000 or (R/'STOP_ALL').exists():
     (case/'STOP').touch();stop_reason=stop_reason or 'resource_progress_or_wall_guard'
    if memory<4*1024**3 or elapsed>51600:
     e.write(case/'critical_resource_stop.json',dict(at=e.stamp(),free_memory_bytes=memory,elapsed_s=elapsed,reason='Owned server critical memory or saving-grace limit'))
     subprocess.run(['taskkill','/PID',str(server_launcher),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
     raise RuntimeError('Critical owned-server resource guard; last checkpoint preserved.')
    if now-last_analysis>=25 and (case/'history.csv').exists():
     screen=evaluate([str(source.parent/'history.csv'),str(case/'history.csv')],plan['period_s'],10,20)
     e.write(case/'cycle_repeatability.json',screen);e.write(R/'wave_cycle_repeatability_current.json',dict(case=case.name,updated_at=e.stamp(),**screen))
     if screen.get('stop_recommended'):
      stop_reason=screen.get('stop_reason') or ('repeatability' if screen.get('stop_for_repeatability') else 'twenty_cycle_review_cap')
      e.write(case/'cycle_stop_decision.json',dict(at=e.stamp(),reason=stop_reason,screen=screen));(case/'STOP').touch()
     last_analysis=now
    if now-last_status>5:
     state('wave_continuation_GPU_running',progress=progress,elapsed_s=elapsed,computation_active=True,period_s=plan['period_s'],cycle_target_min=10,cycle_cap=20,stop_requested=(case/'STOP').exists())
     e.write(R/'queue_state.json',dict(status='running',active=case.name,updated_at=e.stamp(),purpose='W01 cycle-repeatability continuation from saved0.168s'))
     last_status=now
    # A saved completion is authoritative even while an interactive batch client stays connected.
    if (case/'completed.json').exists() or (case/'macro_error.txt').exists():break
    time.sleep(2)
   th.join(2)
  done=e.read(case/'completed.json',{});error=(case/'macro_error.txt').read_text(encoding='utf8') if (case/'macro_error.txt').exists() else None
  preserved=e.digest(source)==sha and e.digest(case/'source_saved_t0.168.sim')==sha
  result=dict(completed=done,source_unchanged=preserved,client_returncode=p.poll(),stop_reason=stop_reason,error=error,elapsed_s=time.time()-started)
  e.write(case/'controller_result.json',result)
  if not done and not error:result['error']='Client exited without completed result; inspect preserved attempt.'
  # Keep the interactive server open after saving; this holder never resumes or starts another solve.
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  while alive(server_pid):
   state('saved_server_open_pending_review' if done else 'needs_review_server_open',progress=done or e.read(case/'progress.json',{}),computation_active=False,server_kept_open=True,result=result,period_s=plan['period_s'],cycle_target_min=10,cycle_cap=20)
   e.write(R/'queue_state.json',dict(status='saved_server_open_pending_review',active=case.name,updated_at=e.stamp()))
   time.sleep(5)
 except BaseException as ex:
  if case.exists():
   (case/'STOP').touch();e.write(case/'controller_error.json',dict(at=e.stamp(),error=e.redact(str(ex))))
  if claimed:state('controller_error_stop_requested',error=e.redact(str(ex)),computation_active=None)
  raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
  # Retain queue lock on an unexpected failure while the server is alive; prevent duplicate starts.
  if not alive(server_pid) or not claimed:
   if e.read(own,{}).get('pid')==os.getpid():own.unlink()
   if e.read(lock,{}).get('pid')==os.getpid():lock.unlink()
if __name__=='__main__':main()
