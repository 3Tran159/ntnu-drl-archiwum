from pathlib import Path
import os,sys,json,re,subprocess,ctypes,time,csv,statistics,hashlib
r=Path(__file__).resolve().parent;h=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');approval=json.loads((h/'audit/LICENSE_USE_APPROVAL.json').read_text());assert approval['approved'];source=Path(approval['source_log']);assert source==h/'runs/RunURANSFromSteady_SP_C_20261102_203650.log'
# Existing explicitly approved task licence; never print it.
line=source.open(encoding='utf8').readline();env=os.environ.copy()
for flag,name in [('-podkey','LM_PROJECT'),('-licpath','CDLMD_LICENSE_FILE')]:
 m=re.search(re.escape(flag)+r'\s+("[^"]+"|\S+)',line);assert m;env[name]=m.group(1).strip('"')
k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];assert k.SetProcessAffinityMask(k.GetCurrentProcess(),1<<4)
exe=r'E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe'
w=Path(r'E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W04_20261103_113831_5d98c0\history.csv')
def w04():
 a=list(csv.DictReader(w.open()));d=[float(b['wall_s'])-float(a['wall_s']) for a,b in zip(a[-61:-1],a[-60:])];return dict(at=time.time(),step=int(a[-1]['step']),median_s=statistics.median(d))
report=[]
for name in ['gap_delta_0','gap_delta_2','sealed_demo_delta_0']:
 out=r/name;assert not (out/'MINI_prepared.sim').exists();assert (out/'mesh_metadata.json').exists();before=w04();t=time.time();env['MINI_CASE_DIR']=str(out)
 with (out/'build.log').open('w',encoding='utf8') as f:
  p=subprocess.Popen([exe,'-power','-np','1','-new','-batch',str(r/'BuildMini.java')],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);print('BUILD_STARTED',name,'PID',p.pid,flush=True);rc=p.wait(timeout=300)
 after=w04();row=dict(case=name,exit_code=rc,build_wall_s=time.time()-t,W04_before=before,W04_after=after,solver_iterations=0);report.append(row);(r/'BUILD_RUNS.json').write_text(json.dumps(report,indent=2));print(json.dumps(row),flush=True)
 if rc!=0 or not (out/'BUILD_STATUS.json').exists():raise RuntimeError('Native build failed; see '+str(out/'build.log'))
 if after['median_s']/before['median_s']>1.15:print('HOLD_W04_RESOURCE_NO_MORE_BUILDS',flush=True);break
print('BUILD_ONLY_COMPLETE; NO CFD SOLVER ITERATIONS EXECUTED',flush=True)
