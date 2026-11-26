from pathlib import Path
import sys,json,datetime,hashlib
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import Polygon,LineString
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
assert run.name.startswith(('c0_tight_cage_v1_','c0_tight_cage_v2_'))
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text(encoding='utf8'));screen=json.loads((run/'cage_geometry_screen.json').read_text(encoding='utf8'))
for name,sha in screen['physical_geometry_sha256'].items():assert hashlib.sha256((h/'geometry/gap_002500um'/name).read_bytes()).hexdigest()==sha
status=json.loads((run/'status.json').read_text(encoding='utf8'));assert status['status']=='mesh_connectivity_prepared' and status['solver_steps']==0
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),physical_source_geometry_unchanged=True,native_contours={},regions={},scientific_approved=False,flow_approval=False)
control=h/'cases/SP_C_split0_overset/c0_layers36_recut_20261103_015428'
polys={}
for name in ['main','flap']:
 d=pd.read_csv(run/(name+'_mesh_native_wall_vertices.csv'))
 coords=np.unique(np.round(d[['X (m)','Z (m)']].to_numpy(),12),axis=0)
 reference=Polygon(g[name+'_polygon']);line=LineString(list(reference.exterior.coords))
 loc=shapely.line_locate_point(line,shapely.points(coords[:,0],coords[:,1]));coords=coords[np.argsort(loc)]
 poly=Polygon(coords);assert poly.is_valid,shapely.is_valid_reason(poly)
 dev=poly.boundary.hausdorff_distance(reference.boundary);area=poly.area/reference.area
 assert .995<area<1.005 and dev<.0005
 row=dict(vertices=len(coords),area_ratio=area,input_hausdorff_m=dev,y_bounds_m=[float(d['Y (m)'].min()),float(d['Y (m)'].max())])
 assert abs(row['y_bounds_m'][0]-.01)<1e-9 and abs(row['y_bounds_m'][1]-.03)<1e-9
 if name=='main':
  a=np.array(json.loads((control/'main_native_polygon.json').read_text(encoding='utf8')))
  tree=shapely.STRtree(shapely.points(a[:,0],a[:,1]));idx=tree.nearest(shapely.points(coords[:,0],coords[:,1]))
  err=np.linalg.norm(coords-a[idx],axis=1)
  row.update(reference_vertices=len(a),unique_matches=len(np.unique(idx)),max_vertex_shift_m=float(err.max()))
  assert len(a)==len(coords)==len(np.unique(idx)) and err.max()<1e-10,'Background physical wall representation changed'
 polys[name]=poly;o['native_contours'][name]=row
 (run/(name+'_native_polygon.json')).write_text(json.dumps(coords.tolist()))
 np.savetxt(run/(name+'_native_polygon.csv'),coords,delimiter=',',header='x_m,z_m',comments='')
for region in ['Background','FlapOverset']:
 d=pd.read_csv(run/(region+'_mesh_full_plane.csv'));active=d[d['Overset Cell Status']==0];p=shapely.points(active['X (m)'].to_numpy(),active['Z (m)'].to_numpy())
 result={name:int(shapely.contains(poly,p).sum()) for name,poly in polys.items()}
 x=d[d['Overset Cell Status']<0]['X (m)']
 o['regions'][region]=dict(plane_centers_inside_native_solids=result,acceptor_x_min_m=float(x.min()),acceptor_x_max_m=float(x.max()),nonactive_upstream_x_lt_0p90m=int(((d['X (m)']<.90)&(d['Overset Cell Status']!=0)).sum()))
 assert not any(result.values()),'Plane-center containment failed; native volume centers require additional check'
assert o['regions']['Background']['nonactive_upstream_x_lt_0p90m']==0,'Forward main-foil layer still intersected'
o['mesh_review']=json.loads((run/'work_mesh_review.json').read_text(encoding='utf8'))
o['technical_screen_pass']=o['mesh_review']['mesh_review_pass']
o['limitation']='Containment uses polygon centers from midspan plane, not true volume-cell centers. Before flow, use initial active-volume export against these native polygons. Technical mesh pass does not establish force accuracy.'
(run/'work_tight_cage_review.json').write_text(json.dumps(o,indent=2))
print(json.dumps(o,indent=2))
