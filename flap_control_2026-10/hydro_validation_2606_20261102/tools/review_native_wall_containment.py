from pathlib import Path
import sys,json,datetime
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h.parent/'flap_poc_2606_20261102/deps'))
import shapely
from shapely.geometry import Polygon,LineString
run=Path(sys.argv[1]).resolve();assert run.is_relative_to(h/'cases/SP_C_split0_overset')
g=json.loads((h/'geometry/gap_002500um/geometry.json').read_text())
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),method='Native boundary vertices projected to corresponding input-contour arclength for ordering. Validity/area/contour deviations verified before active-volume-cell containment. Centers test only; not complete polyhedron intersection audit.',native_contours={},regions={},scientific_approved=False)
polys={}
for name in ['main','flap']:
 reference=Polygon(g[name+'_polygon']);line=LineString(list(reference.exterior.coords))
 a=pd.read_csv(run/(name+'_source_native_wall_vertices.csv'));b=pd.read_csv(run/(name+'_after_native_wall_vertices.csv'))
 coords=np.unique(np.round(a[['X (m)','Z (m)']].to_numpy(),12),axis=0);after=np.unique(np.round(b[['X (m)','Z (m)']].to_numpy(),12),axis=0)
 assert np.array_equal(coords,after),'Native physical wall vertices changed'
 points=shapely.points(coords[:,0],coords[:,1]);loc=shapely.line_locate_point(line,points);coords=coords[np.argsort(loc)]
 poly=Polygon(coords);assert poly.is_valid,shapely.is_valid_reason(poly)
 area=poly.area/reference.area;dev=poly.boundary.hausdorff_distance(reference.boundary)
 assert .995<area<1.005 and dev<.0005,'Contour reconstruction differs materially from input geometry'
 polys[name]=poly
 o['native_contours'][name]=dict(unique_vertices=len(coords),unchanged=True,valid=bool(poly.is_valid),area_m2=poly.area,input_area_ratio=area,hausdorff_deviation_m=dev,y_bounds_m=[float(a['Y (m)'].min()),float(a['Y (m)'].max())])
 (run/(name+'_native_polygon.json')).write_text(json.dumps(coords.tolist()),encoding='utf8')
for reg in ['Background','FlapOverset']:
 r={}
 for label in ['source','after']:
  d=pd.read_csv(run/(reg+'_'+label+'_volume.csv'));d=d[d['Overset Cell Status']==0]
  pts=shapely.points(d['X (m)'].to_numpy(),d['Z (m)'].to_numpy());result={}
  for name,poly in polys.items():
   inside=shapely.contains(poly,pts);depth=shapely.distance(poly.boundary,pts[inside])
   violations=d.loc[inside,['X (m)','Z (m)','Volume (m^3)','Cell Quality']].copy();violations['penetration_m']=depth
   result[name]=dict(centers_inside=int(inside.sum()),max_penetration_m=float(depth.max()) if len(depth) else 0,above_1nm=int((depth>1e-9).sum()),above_1um=int((depth>1e-6).sum()),worst=violations.nlargest(3,'penetration_m').to_dict(orient='records'))
  r[label]=result
 o['regions'][reg]=r
o['active_centers_outside_native_solids']=all(x['above_1nm']==0 for reg in o['regions'].values() for x in reg['after'].values())
o['qualification_caution']='Even a pass establishes center containment only. Native zero donor/error/difficult-stencil audit and unchanged full mesh also required before recovery solve.'
(run/'work_native_wall_containment.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation'/('native_containment_'+run.name+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
print(json.dumps(o,indent=2))
