import json,datetime,shutil
from pathlib import Path
import manual_control_common as c
R=c.R;now=datetime.datetime.now().astimezone().isoformat();policy=c.read(R/'wave_cycle_policy_current.json')
p=R/'wave_cycle_continuation_plan_r2.json';v=c.read(p);v.update(status='running_with_user_early_stop_policy',minimum_assessment_periods=4,typical_periods=10,earliest_assessment_s=4*v['period_s'],stop_rule='Evaluate as soon as four consecutive complete cycles are available and repeatable; ten is a rough expectation, no minimum10periodwait; twenty is diagnostic cap.',policy_override_at=now,policy_file='wave_cycle_policy_current.json');p.write_text(json.dumps(v,indent=2),encoding='utf8')
case=c.W/'W01_W20L4_M10_FS020_cycles_r2';(case/'policy_override.json').write_text(json.dumps(dict(at=now,user_instruction='nie najwczesniej po 10, jak bedzie sie wczesniej nakladac to spoko',**policy),indent=2),encoding='utf8')
p=R/'build_manual_dashboard_copy.py';s=p.read_text(encoding='utf8')
old="    layout.read=lambda key:c.read(R/'control_computer_status.json') if key=='computer_status.json' else original_read(key)"
new="""    def live_read(key):
     if key!='computer_status.json':return original_read(key)
     machine=c.read(R/'control_computer_status.json')
     if machine.get('activity',{}).get('case')=='W01_W20L4_M10_FS020_cycles_r2':
      machine['activity']['description']='W01 saved-state continuation from0.168s. Assess overlapping complete force cycles as soon as available;10periods is indicative only;20periods is the review cap.'
     return machine
    layout.read=live_read"""
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s,encoding='utf8')
print('Current policy: early repeatability; no minimum10 wait. Historical attempt plan preserved with explicit override.')
