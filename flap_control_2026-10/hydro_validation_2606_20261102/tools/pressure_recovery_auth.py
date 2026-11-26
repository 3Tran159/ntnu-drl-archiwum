from pathlib import Path
import json,hashlib
from queue_safety import launch_integrity
from ramp_authorization import blocks
E='INLET_PRESSURE_RECOVERY_20261103'
def authorize_environment(h,name,sim,cpu):
 def read(p):return json.loads(p.read_text(encoding='utf8'))
 cfg=read(h/'NIGHT_QUEUE.json');st=read(h/'NIGHT_QUEUE_STATE.json');intent=st.get('launch_intent',{})
 jobs=[j for j in cfg['jobs'] if j['id']==intent.get('id') and j['macro']==name and Path(j['input'])==sim]
 assert len(jobs)==1,'No matching scoped launch intent'
 j=jobs[0];assert j.get('experiment_id')==E and cpu==j['cpu_processes']==8 and j.get('angle_deg')==0 and j.get('max_steps')==50
 assert not blocks(st,cfg,j),'New failure blocks launch';launch_integrity(h,j)
 assert hashlib.sha256((h/'audit/PRESSURE_RECOVERY_RUNTIME.properties').read_bytes()).hexdigest()==j['runtime_properties_sha256'],'Runtime metadata changed'
 return {'NTNU_PRESSURE_RECOVERY_ALLOWED':'YES'}
