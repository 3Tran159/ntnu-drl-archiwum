"""Timing UI fixture only: tests robust ETA inputs without touching solver histories."""
from pathlib import Path
import csv,json
from wave_cycle_dashboard_panel import _recent_cost
R=Path(__file__).resolve().parent;folder=R/'wave_cycle_dashboard_preview_timing';folder.mkdir(exist_ok=True)
wall=0;rows=[(0,0,0)]
for step in range(1,54):
 wall+=100 if step<=3 or step==30 else 2
 rows.append((step*.001,wall,step))
with (folder/'history.csv').open('w',newline='') as out:
 w=csv.writer(out);w.writerow(['time_s','wall_s','step']);w.writerows(rows)
cost=_recent_cost(folder,.001)
assert cost['available'] and cost['median_s_per_step']==2 and cost['raw_samples']==50 and cost['excluded_timing_outliers']==1 and cost['samples']==49,cost
short=folder/'short';short.mkdir(exist_ok=True)
with (short/'history.csv').open('w',newline='') as out:
 w=csv.writer(out);w.writerow(['time_s','wall_s','step']);w.writerows(rows[:8])
insufficient=_recent_cost(short,.001);assert not insufficient['available']
(R/'wave_cycle_dashboard_preview_timing_qa.json').write_text(json.dumps({'synthetic_fixture_only':True,'pass':True,'robust_sample':cost,'insufficient':insufficient},indent=2),encoding='utf-8')
print('ETA fixture passes: restart delay and pause spike excluded; short history unavailable.')
