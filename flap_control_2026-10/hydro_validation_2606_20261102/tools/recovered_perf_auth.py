from pathlib import Path
import json,hashlib,ctypes,subprocess
from queue_safety import launch_integrity
from ramp_authorization import blocks
E='RECOVERED_PERF_20261103'
def authorize_environment(h,name,sim,cpu):
 def read(p):return json.loads(p.read_text(encoding='utf8'))
 cfg=read(h/'NIGHT_QUEUE.json');st=read(h/'NIGHT_QUEUE_STATE.json');intent=st.get('launch_intent',{})
 jobs=[j for j in cfg['jobs'] if j['id']==intent.get('id') and j['macro']==name and Path(j['input'])==sim]
 assert len(jobs)==1,'No scoped launch intent';j=jobs[0]
 assert j['experiment_id']==E and cpu==j['cpu_processes'] and cpu in [8,12,16,18,20]
 assert not blocks(st,cfg,j);launch_integrity(h,j)
 props=h/'audit/RECOVERED_PERF_RUNTIME.properties';assert hashlib.sha256(props.read_bytes()).hexdigest()==j['runtime_properties_sha256']
 plan=read(h/'cases'/E/'PLAN.json');assert j['input_sha256']==plan['input_sha256'] and j['affinity_mask']==plan['affinity_masks'][str(cpu)]
 assert j['affinity_mask']&3==0 and j['affinity_mask'].bit_count()==cpu
 # Read-only check: W04 stays on its existing mask. No W04 process is modified.
 cmd="(Get-Process -Id 5588 -ErrorAction Stop).ProcessorAffinity.ToInt64()"
 p=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
 assert int(p.stdout.strip())==plan['W04']['affinity_mask'],'W04 allocation changed; review before launch'
 # Only this owned launch helper and its future child inherit the approved mask.
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
 k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetProcessAffinityMask.restype=ctypes.c_int
 assert k.SetProcessAffinityMask(k.GetCurrentProcess(),j['affinity_mask']),'Own launcher affinity failed: '+str(ctypes.get_last_error())
 return {'NTNU_RECOVERED_PERF_ALLOWED':'YES'}
