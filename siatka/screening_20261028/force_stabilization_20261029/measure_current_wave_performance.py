import ctypes,time,json,csv,subprocess,statistics,datetime
from pathlib import Path
R=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
S=json.loads((R/'wave_foil_run_state.json').read_text());A=Path(S['directory'])
k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.c_void_p]*4;k.CloseHandle.argtypes=[ctypes.c_void_p]
class FT(ctypes.Structure):_fields_=[('lo',ctypes.c_uint32),('hi',ctypes.c_uint32)]
def cpu(pid):
 h=k.OpenProcess(0x1000,False,pid)
 if not h:return None
 try:
  x=[FT() for _ in range(4)]
  if not k.GetProcessTimes(h,*[ctypes.byref(i) for i in x]):return None
  return sum((i.hi<<32)+i.lo for i in x[2:])*1e-7
 finally:k.CloseHandle(h)
ids=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',"(Get-Process -Name 'star-ccm+' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json"],text=True))
if isinstance(ids,int):ids=[ids]
start=time.monotonic();before={i:cpu(i) for i in ids};samples=[]
for _ in range(10):
 r=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,utilization.memory,power.draw,temperature.gpu,clocks.current.graphics,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True)
 try:
  vals=[float(x.strip()) for x in r.stdout.strip().split(',')];samples.append(dict(zip(['gpu_pct','memory_controller_pct','power_W','temperature_C','clock_MHz','vram_MiB'],vals)))
 except ValueError:pass
 time.sleep(2)
elapsed=time.monotonic()-start
cpus=[]
for i in ids:
 end=cpu(i)
 if end is not None and before[i] is not None:cpus.append({'pid':i,'cpu_core_equivalents':(end-before[i])/elapsed,'owned_current':i==S['server_pid']})
rows=list(csv.DictReader((A/'history.csv').open()))
pairs=[]
for p,q in zip(rows[-201:-1],rows[-200:]):
 try:
  if int(q['step'])-int(p['step'])==1:pairs.append({'step':int(p['step']),'wall_delta_s':float(q['wall_s'])-float(p['wall_s'])})
 except (ValueError,KeyError):pass
times=[v['wall_delta_s'] for v in pairs if v['wall_delta_s']>0]
d={'updated_at':datetime.datetime.now().astimezone().isoformat(),'case':A.name,'duration_s':elapsed,'gpu_samples':samples,'cpu_samples':sorted(cpus,key=lambda x:x['cpu_core_equivalents'],reverse=True),'recent_step_count':len(times),'last_physical_time_s':float(rows[-1]['time_s']),'median_step_s':statistics.median(times),'mean_step_s':statistics.mean(times),'largest_step_intervals':sorted(pairs,key=lambda x:x['wall_delta_s'],reverse=True)[:8],'topology_workers':S['workers'],'note':'Read-only wall/OS measurement; no change to active solver. CPU core equivalents is process CPU-time / elapsed wall-time, not whole-machine percent.'}
if samples:d['gpu_summary']={q:{'mean':statistics.mean(v[q] for v in samples),'min':min(v[q] for v in samples),'max':max(v[q] for v in samples)} for q in samples[0]}
(R/'wave_runtime_performance_review.json').write_text(json.dumps(d,indent=2))
print(json.dumps({k:v for k,v in d.items() if k not in ['gpu_samples']},indent=2))
