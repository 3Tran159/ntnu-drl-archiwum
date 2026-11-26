import sys,json,csv,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';sys.path.insert(0,str(Q/'deps311'))
import h5py,numpy as np
results=json.loads((R/'configured_mesh_results.json').read_text())['results'];out=[]
for r in results:
 p=Path(r['source_sim']).parent
 with (p/'foil_fields.csv').open() as f:rows=list(csv.DictReader(f))
 xy=np.array([[float(a['X (m)']),float(a['Z (m)'])] for a in rows]);yp=np.array([float(a['Wall Y+']) for a in rows]);weights=np.zeros(len(rows));unmatched=0;largest=0.
 with h5py.File(Q/r['mesh']/'mesh.CGNS','r') as f:
  z=f['Base/fluid'];coords=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ']);g=z['HF_012_wall'];off=g['ElementStartOffset/ data'][...];co=g['ElementConnectivity/ data'][...]-1
  for i in range(len(off)-1):
   points=coords[co[off[i]:off[i+1]]];cent=points[:,[0,2]].mean(0);dist=np.sum((xy-cent)**2,axis=1);idx=int(np.argmin(dist));largest=max(largest,float(np.sqrt(dist[idx])))
   if dist[idx]>1e-14:unmatched+=1;continue
   tri=np.cross(points[1:-1]-points[0],points[2:]-points[0])*.5;weights[idx]+=np.linalg.norm(tri.sum(0))
 assert unmatched==0 and np.all(weights>0),(r['mesh'],unmatched,largest)
 ix=np.argsort(yp);j=np.searchsorted(np.cumsum(weights[ix]),.95*weights.sum());p95=float(yp[ix[j]])
 out.append({'mesh':r['mesh'],'attempt':r['id'],'time_s':r['window'][1],'wall_faces':len(rows),'matched_surface_centroid_max_error_m':largest,'wall_area_m2':float(weights.sum()),'area_weighted_yplus_p95':p95,'wall_area_yplus_below_1_pct':float(100*weights[yp<1].sum()/weights.sum()),'max_yplus':float(yp.max()),'max_location_xz_m':xy[np.argmax(yp)].tolist(),'max_is_not_p95':True,'method':'Exact accepted-wall samples matched to audited CGNS face centres; weights from face area vectors.'})
(R/'configured_wall_yplus_audit.json').write_text(json.dumps({'updated_at':datetime.datetime.now().astimezone().isoformat(),'cases':out},indent=2));print(json.dumps(out,indent=2))
