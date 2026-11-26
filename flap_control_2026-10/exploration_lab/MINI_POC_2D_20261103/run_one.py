from pathlib import Path
import os,sys,json,re,subprocess,ctypes,time,csv,statistics
r=Path(__file__).resolve().parent;h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');case=sys.argv[1];assert case in ['gap_delta_0','gap_delta_2','sealed_demo_delta_0','gap_delta_0_gentle_start'];out=r/case;assert (out/'BUILD_STATUS.json').exists()
resume_api=len(sys.argv)>2 and sys.argv[2]=='--resume-api-error'
if resume_api:
 assert 'Field function is not set' in (out/'SOLVE_ERROR.txt').read_text();archive=out/('api_report_error_attempt_'+str(int(time.time())));archive.mkdir()
 for name in ['history.csv','solve.log','W04_monitor.json','SOLVE_ERROR.txt']:
  p=out/name
  if p.exists():p.replace(archive/name)
else:assert not (out/'history.csv').exists(),'Do not replay a test';assert not (r/'STOP_MINI.json').exists()
# Verify no owned STAR before starting this single, explicitly selected case.
sys.path.insert(0,str(h/'tools'));import night_queue as q
assert not any(p['ownedBatch'] for p in q.processes())
check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^star.*exe$' -and $_.ExecutablePath -like '*21.04.009-R8*'}).Count"],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW);assert int(check.stdout.strip())==0,'Other2606 process active; wait, do not duplicate'
cp=out/('MINI_error.sim' if resume_api else 'MINI_prepared.sim');a=json.loads((h/'audit/LICENSE_USE_APPROVAL.json').read_text());assert a['approved'];source=Path(a['source_log']);assert source==h/'runs/RunURANSFromSteady_SP_C_20261102_203650.log';line=source.open(encoding='utf8').readline();env=os.environ.copy()
for flag,name in [('-podkey','LM_PROJECT'),('-licpath','CDLMD_LICENSE_FILE')]:
 m=re.search(re.escape(flag)+r'\s+("[^"]+"|\S+)',line);assert m;env[name]=m.group(1).strip('"')
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];assert k.SetProcessAffinityMask(k.GetCurrentProcess(),1<<4)
w=Path(r'E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W04_20261103_113831_5d98c0\history.csv')
def sample():
 a=list(csv.DictReader(w.open()));steps=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(a[-41:-1],a[-40:])];return dict(at=time.time(),step=int(a[-1]['step']),median_s=statistics.median(steps))
before=sample();t=time.time();exe=r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe';bad=0;bad_since=None;trace=[]
with (out/'solve.log').open('w',encoding='utf8') as f:
 p=subprocess.Popen([exe,'-power','-np','1','-cpubind','off','-batch',str(r/'SolveMini.java'),str(cp)],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);print('SOLVE_STARTED',case,'PID',p.pid,flush=True)
 while p.poll() is None:
  v=sample();v['slowdown']=v['median_s']/before['median_s']-1;trace.append(v);(out/'W04_monitor.json').write_text(json.dumps(dict(baseline=before,samples=trace),indent=2))
  # Window is40 W04steps;15% guard kept. Stop at next Mini iteration.
  if v['slowdown']>.15:
   if bad_since is None:bad_since=time.time()
   if time.time()-bad_since>=30 and not (r/'STOP_MINI.json').exists():(r/'STOP_MINI.json').write_text(json.dumps(dict(reason='W04_slowdown',baseline=before,observed=v)))
  else:bad_since=None
  time.sleep(5)
 print('SOLVE_EXIT',p.returncode,flush=True)
print((out/'SOLVE_STATUS.json').read_text() if (out/'SOLVE_STATUS.json').exists() else 'HOLD: no final status, inspect solve.log',flush=True)
