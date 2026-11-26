from pathlib import Path
import json,subprocess,time,datetime
from night_queue import processes,resources
h=Path(__file__).resolve().parents[1];st=json.loads((h/'NIGHT_QUEUE_STATE.json').read_text(encoding='utf8'));plist=processes();known=st.get('owned_processes',{})
ids=[p['pid'] for p in plist if known.get(str(p['pid']))==p['born']]
def sample():
 if not ids:return {}
 cmd="Get-Process -Id "+','.join(str(x) for x in ids)+" -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,CPU,WorkingSet64 | ConvertTo-Json -Compress"
 r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 d=json.loads(r.stdout) if r.stdout.strip() else [];d=[d] if isinstance(d,dict) else d
 return {x['Id']:x for x in d}
t0=time.monotonic();a=sample();time.sleep(2);b=sample();dt=time.monotonic()-t0
o=dict(at=datetime.datetime.now().astimezone().isoformat(),active_job=st.get('active',{}).get('id'),owned_processes=len(b),cpu_equivalent_cores=sum(max(0,x.get('CPU',0)-a[k].get('CPU',0)) for k,x in b.items() if k in a)/dt,owned_working_set_GiB=sum(x['WorkingSet64'] for x in b.values())/1024**3,resources=resources(),cpu_mpi_ranks=st.get('active',{}).get('cpu_processes'),gpu_compute=False,ownership='PID and birth-time matched to active queue process tree; native MPI rank count from launch receipt')
(h/'audit/latest_resource_sample.json').write_text(json.dumps(o,indent=2),encoding='utf8');print(json.dumps(o,indent=2))
