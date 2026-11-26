from pathlib import Path
import json,sys,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import LineString
r=Path(sys.argv[1]).resolve();assert r.is_relative_to(h/'cases/SP_C_split0_overset')
line=LineString(json.loads((r/'main_native_polygon.json').read_text())+[json.loads((r/'main_native_polygon.json').read_text())[0]])
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(r),note='Native wall contour and full-plane polygon centers. Layer ordinals inferred geometrically, not native prism index.',profiles={})
for x in [.7556,.7974,.82,.89,.93]:
 stages={}
 for label in ['before','after']:
  d=pd.read_csv(r/('Background_'+label+'_full_plane.csv'));d=d[d['X (m)'].between(x-.004,x+.004)&d['Z (m)'].between(.04,.15)].copy()
  pts=shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy());d['wall_distance_mm']=1000*shapely.distance(line,pts);d['s']=shapely.line_locate_point(line,pts)
  near=d[d.wall_distance_mm<.03];row=near.loc[(near['X (m)']-x).abs().idxmin()];v=d[(d.s-row.s).abs()<.00015].sort_values('wall_distance_mm');v=v[v.wall_distance_mm<20].copy()
  v['geometric_ordinal']=range(1,len(v)+1);acc=v[v['Overset Cell Status']<0];act=v[v['Overset Cell Status']==0]
  stages[label]=dict(first_acceptor_distance_mm=float(acc.wall_distance_mm.min()) if len(acc) else None,max_active_distance_mm=float(act.wall_distance_mm.max()) if len(act) else None,rows=v[['geometric_ordinal','wall_distance_mm','Overset Cell Status','X (m)','Z (m)']].to_dict(orient='records'))
 o['profiles'][str(x)]=stages
(r/'work_interface_placement.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(dict(run=str(r),profiles={x:{k:{q:v for q,v in val.items() if q!='rows'} for k,val in stages.items()} for x,stages in o['profiles'].items()}),indent=2))
