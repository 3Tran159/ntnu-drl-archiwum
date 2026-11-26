from pathlib import Path
import os,json,subprocess,hashlib,re,shutil,time,datetime,ctypes,csv,statistics
R=Path(__file__).resolve().parent;D=R/'active_wave_20261103';H=R.parents[1]/'hydro_validation_2606_20261102';STOP=R/'STOP_MINI.json';LOCK=D/'DAY_CHAIN.lock';STATE=D/'DAY_STATUS.json';deadline=datetime.datetime(2026,11,3,20,30).astimezone().timestamp()
def atom(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');t.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def workers():
 cmd="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('starccm+.exe','star-ccm+.exe') -and $_.ExecutablePath -like '*21.04.009-R8*'}).Count";p=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);return int(p.stdout.strip())
def status(state,stage,**kw):atom(STATE,dict(at=datetime.datetime.now().astimezone().isoformat(),state=state,stage=stage,night_approved=False,CPU=1,GPU=False,**kw))
def preflight():
 assert time.time()<deadline,'Day decision deadline reached; no night authorization';assert not STOP.exists(),'Safety marker requires review';assert workers()==0,'Another STAR active; no duplicate solver';assert shutil.disk_usage(R).free>15*1024**3

def launch(stage,macro,out,source=None,build=False,max_runtime_s=900):
 preflight();out.mkdir(exist_ok=True);compile_run=subprocess.run([r'C:\Program Files\Eclipse Adoptium\jdk-25.0.3.9-hotspot\bin\javac.exe','-encoding','UTF-8','-cp',r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\java\platform\modules\ext\*','-d',str(R/'compiled'),str(R/macro)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert compile_run.returncode==0,compile_run.stderr;shutil.copy2(R/macro,out/macro);log=out/(Path(macro).stem+'.log');assert not log.exists(),'No replay';env=os.environ.copy();env['MINI_CASE_DIR']=str(out)
 args=[EXE,'-power','-np','1','-cpubind','off']+(['-new'] if build else [])+['-batch',str(out/macro)]+([] if build else [str(source)])
 inp=None if build else {'path':str(source),'sha256':sha(source)};atom(out/'RUN_AUTHORIZATION.json',dict(stage=stage,approved_by_user=True,input=inp,macro=macro,macro_sha256=sha(R/macro),scope=globals().get('authorization_scope','Bounded daytime exploration only; gates unchanged; previous HOLD/FAIL untouched'),CPU=1,GPU=False))
 with log.open('w',encoding='utf8') as f:
  p=subprocess.Popen(args,cwd=R,env={**env,**LIC},stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);status('STARTING',stage,PID=p.pid,output=str(out),input=inp);started=time.time();marker_written=False
  while p.poll() is None:
   if time.time()>deadline or time.time()-started>max_runtime_s or shutil.disk_usage(R).free<7*1024**3:
    if not STOP.exists():atom(STOP,dict(source='DAY_CHAIN',reason='deadline_runtime_or_disk',stage=stage));marker_written=True
   # W04 or another GPU-eraSTAR resuming causes our own safe stop; it is not modified.
   cmd="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'star-ccm+.exe' -and $_.ExecutablePath -like '*21.02.007-R8*'}).Count";x=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
   if x.returncode==0 and int(x.stdout.strip() or 0)>0:
    review=json.loads((D/'W04_RESOURCE_REVIEW.json').read_text());rows=list(csv.DictReader(Path(review['history']).open()));deltas=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(rows[-41:-1],rows[-40:])];slow=statistics.median(deltas)/review['baseline_median_step_s']-1
    atom(out/'W04_LATEST.json',dict(at=time.time(),slowdown_fraction=slow,baseline=review['baseline_median_step_s'],current_median=statistics.median(deltas),native_workers=int(x.stdout.strip())))
    if (slow>.15 or int(x.stdout.strip())>1) and not STOP.exists():atom(STOP,dict(source='DAY_CHAIN',reason='W04_resource_guard',stage=stage,slowdown_fraction=slow));marker_written=True
   bindscript="$all=@(Get-CimInstance Win32_Process);$ids=@("+str(p.pid)+");for($n=0;$n -lt 64;$n++){$old=$ids.Count;$ids+=@($all|Where-Object {$_.ParentProcessId -in $ids}|Select-Object -ExpandProperty ProcessId);$ids=@($ids|Select-Object -Unique);if($ids.Count -eq $old){break}};foreach($v in $all|Where-Object {$_.ProcessId -in $ids -and $_.ExecutablePath -like '*21.04.009-R8*'}){$a=Get-Process -Id $v.ProcessId -ErrorAction SilentlyContinue;if($a){$a.ProcessorAffinity=[IntPtr]16}}"
   subprocess.run(['powershell','-NoProfile','-Command',bindscript],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
   hist=out/'history.csv';status('RUNNING' if hist.exists() and hist.stat().st_size>100 else 'STARTING',stage,PID=p.pid,output=str(out),safe_stop_requested=marker_written)
   time.sleep(5)
  assert p.returncode==0,'Native stage failed; inspect log, no next stage'
 if build:
  assert json.loads((out/'BUILD_STATUS.json').read_text())['status']=='BUILT_NOT_SOLVED';return 'BUILT'
 fn='KINEMATICS_STATUS.json' if macro=='ProbeMiniMorpher.java' else 'SOLVE_STATUS.json';res=json.loads((out/fn).read_text());atom(out/'CHECKPOINT_MANIFEST.json',[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in out.glob('*.sim')]);return res['status']
EXE=r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe'
a=json.loads((H/'audit/LICENSE_USE_APPROVAL.json').read_text());assert a['approved'];license_source=Path(a['source_log']);assert license_source==H/'runs/RunURANSFromSteady_SP_C_20261102_203650.log';line=license_source.open(encoding='utf8').readline();LIC={}
for flag,key in [('-podkey','LM_PROJECT'),('-licpath','CDLMD_LICENSE_FILE')]:
 m=re.search(re.escape(flag)+r'\s+("[^"]+"|\S+)',line);assert m;LIC[key]=m.group(1).strip('"')
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];assert k.SetProcessAffinityMask(k.GetCurrentProcess(),1<<4)
def main():
 with LOCK.open('x') as f:json.dump(dict(pid=os.getpid(),created=time.time()),f)
 try:
  # Same saved fields and equation definitions; one numerical URF correction only.
  out=R/'sealed0_fast_20261103';out.mkdir(exist_ok=True);src=R/'sealed0_continue_20261103/MINI_result.sim';assert not (out/'ContinueSealedFast.log').exists();assert sha(out/'input.sim')==sha(src);res=launch('SEALED0_NUMERICAL_CONTINUATION','ContinueSealedFast.java',out,out/'input.sim')
  if res!='NUMERICAL_POC_STABILIZED_NOT_VALIDATED':status('HOLD','SEALED0',reason=res);raise SystemExit(0)
  status('PASS_STAGE','SEALED0',checkpoint=str(out/'MINI_result.sim'))
  plus=R/'sealed_c2_delta_2';launch('SEALED_PLUS2_BUILD','BuildMini.java',plus,build=True);res=launch('SEALED_PLUS2_SOLVE','SolveSealedPlus2.java',plus,plus/'MINI_prepared.sim')
  if res!='NUMERICAL_POC_STABILIZED_NOT_VALIDATED':status('HOLD','SEALED_PLUS2',reason=res);raise SystemExit(0)
  probe=R/'sealed_motion_probe_20261103';probe.mkdir();shutil.copy2(out/'MINI_result.sim',probe/'input.sim');res=launch('MORPHER_2D_KINEMATICS','ProbeMiniMorpher.java',probe,probe/'input.sim')
  status('DAY_COMPLETE' if res=='PASS_KINEMATICS_ONLY' else 'HOLD','KINEMATICS',reason=res,next='Work review; orbital field CFD and active-flow tests still pending; no night start')
 except Exception as e:status('HOLD','CONTROLLER',reason=str(e));raise
 finally:
  LOCK.unlink(missing_ok=True)

if __name__=='__main__':main()
