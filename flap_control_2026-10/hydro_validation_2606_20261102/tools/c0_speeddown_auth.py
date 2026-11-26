"""Deliver the macro marker only after the existing queue's scoped approval checks."""
from pathlib import Path
import json
from queue_safety import launch_integrity
from ramp_authorization import blocks
def authorize_environment(h,name,sim,cpu):
 def read(p):return json.loads(p.read_text(encoding='utf8'))
 cfg=read(h/'NIGHT_QUEUE.json');st=read(h/'NIGHT_QUEUE_STATE.json');intent=st.get('launch_intent',{})
 jobs=[j for j in cfg['jobs'] if j['id']==intent.get('id') and j['macro']==name and Path(j['input'])==sim]
 assert len(jobs)==1,'No matching authorized launch intent'
 j=jobs[0];assert j.get('experiment_id')=='C0_SPEED_DOWN_20261103' and cpu==j['cpu_processes']==8 and j.get('angle_deg')==0
 assert not blocks(st,cfg,j),'Scoped approval blocked';launch_integrity(h,j)
 return {'NTNU_C0_SPEEDDOWN_ALLOWED':'YES'}
