"""Check reported units, force balance and the timing statistic against recorded data."""
import csv,statistics,json
from pathlib import Path
import mesh_convergence_candidate as mc
R=Path(__file__).resolve().parent
d=mc.assess(persist=False)
assert {'M02','M03','M04','M05'}<={r['id'] for r in d['settled_results']}
jobs=json.loads((R/'queue.json').read_text())
for r in d['settled_results']:
    assert abs(r['force_balance_error_N'])<1e-7,r
    assert r['timing_intervals']>=198,r
    assert r['observed_inner_iterations_per_step']==20,r
    job=[j for j in jobs if j['id'].startswith(r['id']+'_')][-1]
    with (R/job['id']/'history.csv').open() as f:history=list(csv.DictReader(f))
    win=[x for x in history if r['window_start_s']+1e-8<float(x['physical_time_s'])<=r['time_s']+1e-8]
    for field,source in [('Fx_pressure_N','pressure_drag_N'),('Fx_viscous_N','viscous_drag_N')]:
        assert abs(r[field]-statistics.mean(float(x[source]) for x in win))<1e-8,(r['id'],field)
    assert abs(r['solver_wall_s_per_physical_s']*.001-r['wall_s_per_step_mean'])<1e-8,r
p=next(x for x in d['comparisons'] if x['coarse']=='M03' and x['fine']=='M05')
assert not p['within_1pct'] and p['force_component_delta_pct']['Fx_pressure_N']>0 and p['force_component_delta_pct']['Fx_viscous_N']<0
print(json.dumps({'verified':[{k:r[k] for k in ['id','Fx_pressure_N','Fx_viscous_N','Fx_total_N','wall_s_per_step_median','wall_s_per_step_mean','timing_intervals']} for r in d['settled_results']],'M03_vs_M05':p},indent=2))
