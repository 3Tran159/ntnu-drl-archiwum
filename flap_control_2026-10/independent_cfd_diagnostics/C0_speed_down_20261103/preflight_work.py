from pathlib import Path
import sys,json
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'tools'));import night_queue as q
from queue_safety import launch_integrity
from ramp_authorization import blocks
from c0_speeddown_auth import authorize_environment
cfg=q.read(q.CFG);st=q.read(q.STATE);q.validate(cfg)
pending=[j for j in cfg['jobs'] if j['id'] not in st['jobs'] and not j.get('disabled')]
assert len(pending)==1 and pending[0]['id']=='C0_SPEED_DOWN_20261103_SMOKE'
j=pending[0];assert st.get('active') is None and not any(p['ownedBatch'] for p in q.processes());launch_integrity(H,j)
assert not blocks(st,cfg,j)
for old in ['plus2_benchmark_8cpu_20261103','RAMP_C0_PLUS2_S5_20261103_RUN','SPEED_SWEEP_PLUS2_20261103_SMOKE']:
 assert st['jobs'][old]['state']=='failed' and not cfg.get('release_failure_hold',{}).get(old)
 assert blocks(st,cfg,next(x for x in cfg['jobs'] if x['id']==old))
try:authorize_environment(H,j['macro'],Path(j['input']),8)
except AssertionError:pass
else:raise AssertionError('Native marker must be denied without authorized controller launch intent')
for name in ['STOP_OWNED_CFD.json','PAUSED_FOR_HOME.json']:assert not (H.parent/name).exists()
rs=q.resources();assert rs['ram_available_GiB']>=16 and rs['disk_free_GiB']>=18
result=dict(at=q.now(),preflight='PASS',job=j['id'],cpu=8,gpu=False,other_pending_jobs=0,owned_solver_active=False,old_failures_preserved=True,native_marker_requires_scoped_controller_intent=True,resources=rs)
q.atomic(D/'WORK_PREFLIGHT.json',result)
if '--enable-short-test' in sys.argv:
 cfg.update(accept_new_jobs=True,controller_exit_requested=False);q.atomic(q.CFG,cfg);q.event('c0_speeddown_short_test_enabled',preflight=result)
print(json.dumps(result,indent=2))
