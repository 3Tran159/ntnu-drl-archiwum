from pathlib import Path
import json,hashlib
from queue_safety import launch_integrity
from ramp_authorization import blocks
E='RECOVERED_PERF_20261103'
def authorize_environment(h,name,sim,cpu):
 def read(p):return json.loads(p.read_text(encoding='utf8'))
 cfg=read(h/'NIGHT_QUEUE.json');st=read(h/'NIGHT_QUEUE_STATE.json');intent=st.get('launch_intent',{})
 jobs=[j for j in cfg['jobs'] if j['id']==intent.get('id') and j['macro']==name and Path(j['input'])==sim]
 assert len(jobs)==1;j=jobs[0];assert j['experiment_id']==E and j['kind']=='perf_production'
 assert not blocks(st,cfg,j);launch_integrity(h,j)
 d=h/'cases'/E;plan=read(d/'PLAN.json');selected=read(d/'SELECTED_CONFIG.json')
 assert hashlib.sha256((d/'SELECTED_CONFIG.json').read_bytes()).hexdigest()==j['selection_sha256']
 assert selected['cpu_processes']==j['cpu_processes']==cpu and selected['dt_s']==j['dt_s']==.002
 assert selected['diagnostic_resumption_authorized'] and not selected['static_validation_claimed']
 assert j['input_sha256']==plan['input_sha256'] and sim==Path(plan['production_checkpoint']['path'])
 assert j['affinity_mask']==plan['affinity_masks'][str(cpu)] and j['affinity_mask']&3==0
 assert hashlib.sha256((h/'audit/OPTIMIZED_RECOVERED_RUNTIME.properties').read_bytes()).hexdigest()==j['runtime_properties_sha256']
 import ctypes
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.c_void_p
 k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetProcessAffinityMask.restype=ctypes.c_int
 assert k.SetProcessAffinityMask(k.GetCurrentProcess(),j['affinity_mask']),'Own launcher affinity failed: '+str(ctypes.get_last_error())
 return {'NTNU_OPTIMIZED_PRODUCTION_ALLOWED':'YES'}
