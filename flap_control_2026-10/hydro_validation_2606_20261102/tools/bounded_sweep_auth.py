from pathlib import Path
import json,hashlib
from queue_safety import launch_integrity
from ramp_authorization import blocks
E='BOUNDED_FIXED_PLUS2_SWEEP_20261103'
def authorize_environment(h,name,sim,cpu):
 def read(p):return json.loads(p.read_text(encoding='utf8'))
 cfg=read(h/'NIGHT_QUEUE.json');st=read(h/'NIGHT_QUEUE_STATE.json');intent=st.get('launch_intent',{})
 jobs=[j for j in cfg['jobs'] if j['id']==intent.get('id') and j['macro']==name and Path(j['input'])==sim]
 assert len(jobs)==1,'No matching scoped launch intent'
 j=jobs[0];expected={'BoundedFixedFlapSweep.java':E,'RecoveredFixedFlapSweep.java':'RECOVERED_FIXED_PLUS2_SWEEP_20261103'}[name];assert j.get('experiment_id')==expected and cpu==j['cpu_processes']==8 and j.get('angles_deg')==[0,2] and j.get('speeds_m_s')==[10,12,14,16,18]
 assert not blocks(st,cfg,j),'New failure blocks launch';launch_integrity(h,j)
 assert hashlib.sha256((h/'audit'/('RECOVERED_SWEEP_RUNTIME.properties' if name=='RecoveredFixedFlapSweep.java' else 'BOUNDED_SWEEP_RUNTIME.properties')).read_bytes()).hexdigest()==j['runtime_properties_sha256'],'Resume phase metadata changed'
 return {'NTNU_BOUNDED_SWEEP_ALLOWED':'YES'}
