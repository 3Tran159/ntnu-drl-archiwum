import json
from pathlib import Path
r=Path(r'F:/ntnu/mesh_screening_20261028/force_stabilization_20261029')
for name in ['queue_state.json','M06_ready.json','settled_post_error.json','selected_snapshots.json','yplus_summary.json']:
 p=r/name
 if not p.exists():continue
 try:a=json.loads(p.read_text(encoding='utf-8-sig'))
 except Exception as e:print(name,type(e).__name__);continue
 if name=='selected_snapshots.json':a={k:{n:v.get(n) for n in ['time_s','status']} for k,v in a.items()}
 if name=='yplus_summary.json':a={k:{n:v.get(n) for n in ['snapshot_time_s','area_mean','max','area_weighted_p95','max_at_x_over_c','max_at_continuous_layers','area_fraction_pct']} for k,v in a.items() if isinstance(v,dict) and k.startswith('M')}
 print(name,json.dumps(a,ensure_ascii=True))
