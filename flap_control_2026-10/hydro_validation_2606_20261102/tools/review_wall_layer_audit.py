from pathlib import Path
import sys,json,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import Polygon
run=Path(sys.argv[1]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset')
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
polys={n:Polygon(g[n+'_polygon']) for n in ['main','flap']}
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),scientific_approved=False,geometry_caution='Inside cell-centroid test, not full polyhedron intersection; polygon/tessellation micrometre differences reported without silently treating them as exact geometry.',regions={})
for reg in ['Background','FlapOverset']:
 a=pd.read_csv(run/(reg+'_source_volume.csv'));b=pd.read_csv(run/(reg+'_after_volume.csv'))
 r=dict(source_rows=len(a),after_rows=len(b),geometry={})
 for label,d in [('source',a),('after',b)]:
  d=d[d['Overset Cell Status']==0]
  pts=shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy())
  rr={}
  for name,poly in polys.items():
   inside=shapely.contains(poly,pts);depth=shapely.distance(poly.boundary,pts[inside])
   rr[name]=dict(active_centers_inside=int(inside.sum()),max_penetration_m=float(depth.max()) if len(depth) else 0,above_10um=int((depth>1e-5).sum()),above_100um=int((depth>1e-4).sum()))
  r['geometry'][label]=rr
 fa=pd.read_csv(run/(reg+'_before_full_plane.csv'));fb=pd.read_csv(run/(reg+'_after_full_plane.csv'))
 xyz=['X (m)','Y (m)','Z (m)']
 tree=shapely.STRtree(shapely.points(fa['X (m)'].to_numpy(),fa['Z (m)'].to_numpy()))
 idx=tree.nearest(shapely.points(fb['X (m)'].to_numpy(),fb['Z (m)'].to_numpy()))
 matched=fa.iloc[idx].reset_index(drop=True)
 r['full_mesh']=dict(source_cells=len(fa),after_cells=len(fb),unique_matches=len(np.unique(idx)),max_coordinate_difference_m=float(np.abs(fb[xyz].to_numpy()-matched[xyz].to_numpy()).max()),max_volume_relative_difference=float(np.abs(fb['Volume (m^3)'].to_numpy()/matched['Volume (m^3)'].to_numpy()-1).max()),status_changes=int((fb['Overset Cell Status'].to_numpy()!=matched['Overset Cell Status'].to_numpy()).sum()),error_cells=int((fb['Overset Error Status']!=0).sum()),difficult_cells=int(fb['Overset Interpolation Type'].between(4,6).sum()))
 o['regions'][reg]=r
o['connectivity_changed']=any(r['full_mesh']['status_changes']>0 for r in o['regions'].values())
o['flow_continuation_approved']=False
o['conclusion']='No measured hole-cutting change; cannot approve wall-protection remedy until native connectivity is actually recomputed and checked.' if not o['connectivity_changed'] else 'Connectivity changed; detailed native/geometry review required.'
(run/'work_wall_layer_audit.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation'/('wall_layer_audit_'+run.name+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
