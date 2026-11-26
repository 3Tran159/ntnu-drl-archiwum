"""Unique halfdt C01 diagnostic. No wave, no automatic acceptance, no resumed failed fields."""
from pathlib import Path
import os,sys,json,time,subprocess,threading,ctypes,shutil,csv,math,statistics,uuid
import local_control_model as m
import local_control_worker as w
import run_until_settled as e
R=m.R;W=m.W;A=W/'LOCAL_C01_dt05ms_probe_r3';P=W/'C01_W20L4_M10_calm_settle_r2';SOURCE=P/'checkpoint_t1.837.sim'
EXPECTED='fff17db8bc5e69f48ddb55289bb313120b0fd3ec0f030bd11fecad75f4e0dd92'
def state(status,**kw):
 m.write(R/'wave_foil_run_state.json',dict(status=status,case=A.name,directory=str(A),controller_pid=os.getpid(),updated_at=m.stamp(),gpu=True,workers=1,computation_stage='calm_settling',diagnostic_only=True,dt_s=.0005,source_time_s=1.837,scope='C01 half-timestep diagnostic only:1.837 to2.900s;dt0.5ms,10inner; no wave or automatic settled-reference admission',formal_wave_force_acceptance=False,user_mass_exception=True,manual_request=dict(target_s=2.9,wall_minutes=90),**kw))
def review(done,preserved):
 rows=list(csv.DictReader((A/'history.csv').open()));native=list(csv.DictReader((A/'native_phase_budget.csv').open()))
 values=lambda rs,key:[float(r[key]) for r in rs if r.get(key) and math.isfinite(float(r[key]))]
 peak=max(values(rows,'max_speed_m_s'),default=None);nm=max(values(native,'native_abs_sum_pct_inward_mass'),default=None)
 reference={round(float(r['time_s']),6):r for r in csv.DictReader((P/'history.csv').open())}
 common=[(r,reference.get(round(float(r['time_s']),6))) for r in rows];common=[(a,b) for a,b in common if b]
 diffs={k:max([abs(float(a[k])-float(b[k])) for a,b in common],default=None) for k in ['CD','CL_total','max_speed_m_s','interface_CFL']}
 out=dict(case=A.name,status='short_diagnostic_completed_pending_scientific_review' if done.get('status')=='target_reached' else 'diagnostic_stopped_requires_review',completed=done,source_unchanged=preserved,source_time_s=1.837,target_time_s=2.9,dt_s=.0005,inner=10,checkpoint_interval_s=.05,history_rows=len(rows),native_steps=len(native),max_history_speed_m_s=peak,native_abs_mass_peak_pct=nm,mass_review_limit_pct=.01,mass_review_pass=(nm is not None and nm<.01),all_halfsteps_retained=True,common_reference_samples=len(common),maximum_absolute_difference_at_common_times=diffs,reference_case=P.name,reference_stopped_at_s=2.777,calm_reference_accepted=False,waves_admitted=False,source_file=str(SOURCE),computed_file=str(A/'final.sim'),note='Onlyglobaldtchanged. No automaticcalm/waveacceptance. FirstnewexternalBDF2isundefinedmixedspacing; nativephaseerrorsretained everyhalfstep. Reviewlocalgrowthandcalmsettling separately.',updated_at=m.stamp())
 m.write(R/'c01_halfdt_probe_r3_review.json',out);m.write(A/'review.json',out);return out
def main():
 if sys.argv[1:]!=['--run']:raise RuntimeError('Use --run')
 if (R/'local_control/PAUSE').exists() or m.read(R/'campaign_hold.json').get('active'):raise RuntimeError('User hold: wait for mesh review and explicit resume')
 if A.exists() or (R/'c01_halfdt_probe_r3.consumed').exists() or (R/'STOP_ALL').exists():raise RuntimeError('Attempt/stop exists; neverrestart')
 if not w.safe_ready():raise RuntimeError('Own campaign process orlock remains; no duplicate')
 if e.free_memory()<24*1024**3 or shutil.disk_usage(W).free<40*1024**3:raise RuntimeError('Need24GiB RAM/40GiBdisk forfrequentcheckpoints')
 receipt=m.read(R/'c01_halfdt_probe_r3_build_receipt.json');macro=R/'C01HalfDtProbeR3.java'
 if receipt.get('status')!='javac_passed' or e.digest(macro)!=receipt.get('macro_sha256'):raise RuntimeError('Compiledmacroidentity failed')
 if e.digest(SOURCE)!=EXPECTED:raise RuntimeError('Pre-growthcheckpointidentity failed')
 rows=list(csv.DictReader((P/'history.csv').open()));fp=next(r for r in rows if abs(float(r['time_s'])-1.837)<1e-8)
 mapping=dict(speed='max_speed_m_s',mass='mass_kg',water_volume='water_volume_m3',Fx='Fx_slice_N',Fz='Fz_slice_N',pressure_drag='pressure_drag_N',viscous_drag='viscous_drag_N')
 token=uuid.uuid4().hex;lock=R/'queue.lock';own=R/'c01_halfdt_probe_r3.lock';proc=None
 try:
  w.own_lock(lock,token,A.name);w.own_lock(own,token,A.name)
  with (R/'c01_halfdt_probe_r3.consumed').open('x') as f:f.write(m.stamp())
  A.mkdir();shutil.copy2(SOURCE,A/'input.sim');shutil.copy2(macro,A/macro.name)
  if e.digest(A/'input.sim')!=EXPECTED:raise RuntimeError('Copiedcheckpointidentity failed')
  m.write(A/'source_identity.json',dict(source=str(SOURCE),source_sha256=EXPECTED,input_sha256=EXPECTED,source_time_s=1.837,source_cells=317277,source_calm_settled=False,source_is_guard_failed=False,parent_attempt_later_failed=True,reinitialized=False,height_m=0,wavelength_m=20,depth_m=24,mesh=str(W/'C01_W20L4_M10_FS020_mesh_r2/mesh.CGNS'),review=str(R/'c01_calm_r2_next_diagnostic_review.json')))
  m.write(A/'request.json',dict(diagnostic_only=True,spec=dict(name='C01 half-dt diagnostic',height_m=0,wavelength_m=20,dt_s=.0005,inner=10,xmin_m=-35,xmax_m=45,target_time_s=2.9),checkpoint_interval_s=.05,source_field_fingerprint=fp,created_at=m.stamp()))
  env=dict(os.environ,NTNU_WAVE_OUT=str(A),NTNU_MODE='calm',NTNU_SOURCE_TIME='1.837',NTNU_WAVE_DT='.0005',NTNU_WAVE_STEPS='2126',NTNU_WAVE_CELLS='317277',NTNU_WAVE_HEIGHT='0',NTNU_WAVE_WALL_S='5400',NTNU_CFG_XMIN='-35',NTNU_CFG_XMAX='45',NTNU_CFG_LAMBDA='20',NTNU_CFG_GAUGES='-10,-5,2.5,5,10,15,20',NTNU_ZONE='20')
  for k,v in mapping.items():env['NTNU_FP_'+k]=fp[v]
  k=ctypes.windll.kernel32;k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
  if not k.SetProcessAffinityMask(k.GetCurrentProcess(),3):raise RuntimeError('CannotreserveCPU0/1')
  k.SetPriorityClass(k.GetCurrentProcess(),0x20);k.SetThreadExecutionState(0x80000001)
  start=time.monotonic();last_t=1.837;last_change=start;stop_at=None
  with (A/'star.log').open('x',encoding='utf8') as log:
   proc=subprocess.Popen([str(e.STAR),*e.saved_options(1),'-gpgpu','auto:1','-batch',str(A/macro.name),str(A/'input.sim')],cwd=A,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW|subprocess.NORMAL_PRIORITY_CLASS)
   m.write(A/'process.json',dict(launcher_pid=proc.pid,controller_pid=os.getpid(),gpu=True,workers=1,started_at=m.stamp()))
   def drain():
    for line in proc.stdout:log.write(e.redact(line));log.flush()
   th=threading.Thread(target=drain,daemon=True);th.start()
   while proc.poll() is None:
    p=m.read(A/'progress.json');now=time.monotonic();pt=p.get('time_s',1.837)
    if pt>last_t:last_t=pt;last_change=now
    state('C01_halfdt_diagnostic_running',computation_active=True,launcher_pid=proc.pid,progress=p,elapsed_s=now-start,stop_requested=(A/'STOP').exists())
    issue=(R/'STOP_ALL').exists() or e.free_memory()<8*1024**3 or shutil.disk_usage(W).free<8*1024**3 or now-start>5700 or now-last_change>(900 if last_t==1.837 else 600)
    if issue:(A/'STOP').touch()
    if (A/'STOP').exists() and stop_at is None:stop_at=now
    if stop_at and now-stop_at>600:
     subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);raise RuntimeError('Owneddiagnosticexceededsavegrace')
    time.sleep(2)
   rc=proc.wait();th.join(10)
  done=m.read(A/'completed.json');preserved=e.digest(SOURCE)==EXPECTED and e.digest(A/'input.sim')==EXPECTED
  result=dict(returncode=rc,source_unchanged=preserved,completed=done,diagnostic_only=True,elapsed_s=time.monotonic()-start,waves_admitted=False)
  m.write(A/'controller_result.json',result)
  if rc==0 and preserved and (A/'history.csv').exists() and (A/'native_phase_budget.csv').exists():review(done,preserved)
  state('C01_halfdt_diagnostic_saved_requires_review',computation_active=False,result=result,progress=done)
 except BaseException as ex:
  if proc is not None and proc.poll() is None:
   (A/'STOP').touch()
   try:proc.wait(timeout=600)
   except subprocess.TimeoutExpired:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  if A.exists():m.write(A/'controller_error.json',dict(error=e.redact(str(ex)),at=m.stamp()))
  state('needs_review',computation_active=False,error=e.redact(str(ex)));raise
 finally:
  ctypes.windll.kernel32.SetThreadExecutionState(0x80000000);w.release(own,token);w.release(lock,token)
if __name__=='__main__':main()
