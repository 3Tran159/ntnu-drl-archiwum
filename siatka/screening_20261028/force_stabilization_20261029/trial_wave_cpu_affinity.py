"""Reversible OS-only A/B/A affinity timing for the already-owned live STAR process."""
import ctypes,json,time,datetime,csv,statistics,subprocess,os
from ctypes import wintypes as w
from pathlib import Path
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def stamp():return datetime.datetime.now().astimezone().isoformat()
s=read(R/'wave_foil_run_state.json');case=Path(s['directory']);pid=s['server_pid']
audit=read(R/'wave_cpu_affinity_audit.json')
if pid!=36856 or s['controller_pid']!=37216 or read(R/'queue.lock')['pid']!=37216 or not s.get('computation_active'):raise RuntimeError('Owned running identity changed')
if not all(any(q['logical_cpu']==i and q['group']==0 and q['efficiency_class']==1 for q in audit['cpu_sets']) for i in [0,1]):raise RuntimeError('Requested fast CPU mapping not confirmed')
k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.restype=w.HANDLE;k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.CloseHandle.argtypes=[w.HANDLE]
k.GetProcessAffinityMask.argtypes=[w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)];k.SetProcessAffinityMask.argtypes=[w.HANDLE,ctypes.c_size_t]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
h=k.OpenProcess(0x1000|0x0200,False,pid)
if not h:raise ctypes.WinError(ctypes.get_last_error())
buf=ctypes.create_unicode_buffer(32768);size=w.DWORD(len(buf))
if not k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(size)) or not buf.value.lower().endswith('star-ccm+.exe'):raise RuntimeError('Unexpected executable')
orig=ctypes.c_size_t();system=ctypes.c_size_t()
if not k.GetProcessAffinityMask(h,ctypes.byref(orig),ctypes.byref(system)):raise ctypes.WinError(ctypes.get_last_error())
if orig.value!=audit['process_affinity_mask'] or not (system.value&3)==3:raise RuntimeError('Affinity changed before test')
out=R/'wave_cpu_affinity_trial.json';d=dict(started_at=stamp(),server_pid=pid,case=case.name,original_mask=orig.value,test_mask=3,numerical_changes=False,other_processes_changed=False,stages=[],status='running')
def save():out.write_text(json.dumps(d,indent=2),encoding='utf8')
def setmask(mask):
 if not k.SetProcessAffinityMask(h,mask):raise ctypes.WinError(ctypes.get_last_error())
 q=ctypes.c_size_t();r=ctypes.c_size_t()
 if not k.GetProcessAffinityMask(h,ctypes.byref(q),ctypes.byref(r)) or q.value!=mask:raise RuntimeError('Affinity getter mismatch')
def latest():
 rr=list(csv.DictReader((case/'history.csv').open()));return rr
def stage(name):
 start_rows=latest();start_step=int(start_rows[-1]['step']);gp=[];start=time.monotonic()
 while time.monotonic()-start<45:
  cur=read(R/'wave_foil_run_state.json')
  if cur['server_pid']!=pid or not cur.get('computation_active') or (case/'STOP').exists():raise RuntimeError('Calculation ended or stop requested; restore affinity')
  r=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,power.draw','--format=csv,noheader,nounits'],capture_output=True,text=True)
  try:gp.append([float(x) for x in r.stdout.strip().split(',')])
  except ValueError:pass
  time.sleep(2)
 rr=latest();intervals=[]
 for a,b in zip(rr,rr[1:]):
  st=int(a['step'])
  if st>=start_step+2 and st%50!=0 and st%500!=0 and int(b['step'])==st+1:
   delta=float(b['wall_s'])-float(a['wall_s'])
   if delta>0:intervals.append(delta)
 row=dict(stage=name,completed_at=stamp(),start_time_s=float(start_rows[-1]['time_s']),end_time_s=float(rr[-1]['time_s']),ordinary_steps=len(intervals),median_step_s=statistics.median(intervals) if intervals else None,mean_step_s=statistics.mean(intervals) if intervals else None,gpu_mean_pct=statistics.mean(g[0] for g in gp) if gp else None,gpu_power_mean_W=statistics.mean(g[1] for g in gp) if gp else None)
 d['stages'].append(row);save();print(json.dumps(row),flush=True);return row
keep=False
try:
 save();a=stage('A_original_affinity')
 setmask(3);d['current_mask']=3;save();print('Own solver now restricted to CPU0/1; numerical settings unchanged.',flush=True)
 b=stage('B_CPU0_CPU1')
 setmask(orig.value);d['current_mask']=orig.value;save()
 a2=stage('A2_original_affinity')
 if min(x['ordinary_steps'] for x in [a,b,a2])<10:raise RuntimeError('Insufficient regular-step observations')
 ref=(a['median_step_s']+a2['median_step_s'])/2;gain=100*(1-b['median_step_s']/ref)
 # Require improvement against both bracketing reference windows; no numerical acceptance inferred.
 keep=b['median_step_s']<.95*min(a['median_step_s'],a2['median_step_s'])
 if keep:setmask(3)
 d.update(status='completed',current_mask=3 if keep else orig.value,kept_CPU0_CPU1=keep,median_step_reduction_pct=gain,interpretation='Sequential live-run timing; physical state changes across windows. Requires improvement against both reference windows; no claim of exact matched-state benchmark.',ended_at=stamp());save();print(json.dumps(d),flush=True)
except BaseException as ex:
 d.update(status='error_restored_original',error=str(ex),ended_at=stamp());save();raise
finally:
 if not keep:setmask(orig.value)
 k.CloseHandle(h)
