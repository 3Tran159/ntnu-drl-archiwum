from pathlib import Path
import sys,json
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely import Polygon,STRtree
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text());wall=Polygon(g['main_polygon']).boundary
paths={'control':h/'cases/SP_C_split0_overset/c0_distance_20261102_232050','overlap1mm':h/'cases/SP_C_split0_overset/c0_overlap_distance_audit_20261103_002542','patch05mm':h/'cases/SP_C_split0_overset/c0_overlap_patch05mm_20261103_003057'}
o={'coordinate_caution':'Distances use full-plane sample coordinates, not exact volume-cell centroids; for interface-location comparison only. Same native foil polygon. x[.74,.91] excludes hinge gap.','cases':{}}
bands=[0,.0001,.0005,.001,.002,.005,.01,.02]
for label,folder in paths.items():
 tag='final' if label=='control' else 'mesh';rec={};o['cases'][label]=rec
 for region in ['Background','FlapOverset']:
  d=pd.read_csv(folder/(region+'_'+tag+'_full_plane.csv'));d=d[d['X (m)'].between(.74,.91)].copy()
  distance=shapely.distance(shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy()),wall);d['wall_distance_geom_m']=distance
  a=d[(d['Overset Cell Status']<0)&(distance<.02)]
  rec[region]={'acceptors_near_profile':len(a),'acceptor_distance_quantiles_m':{str(q):float(a.wall_distance_geom_m.quantile(q)) for q in [.0,.1,.5,.9,1.]},'active_cells_by_distance_band':[]}
  for lo,hi in zip(bands[:-1],bands[1:]):rec[region]['active_cells_by_distance_band'].append({'lo_m':lo,'hi_m':hi,'cells':int(((d['Overset Cell Status']==0)&(distance>=lo)&(distance<hi)).sum())})
(h/'validation/overlap_nearwall_activation.json').write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
