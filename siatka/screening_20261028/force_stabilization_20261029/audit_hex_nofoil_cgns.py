import sys,json,datetime
from pathlib import Path
sys.path.insert(0,r'F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\deps311')
import numpy as np,h5py
p=Path(sys.argv[1]).resolve()
with h5py.File(p/'mesh.CGNS','r') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 cg=z['fluid'];assert int(cg[' data'][0])==17
 cn=cg['ElementConnectivity/ data'][...].reshape(-1,8)-1;pts=xyz[cn];lo=pts.min(1);hi=pts.max(1);delta=hi-lo
 volumes=np.prod(delta,axis=1);cent=(lo+hi)/2
 corners=np.all(np.isclose(pts,lo[:,None,:],atol=1e-10)|np.isclose(pts,hi[:,None,:],atol=1e-10))
 unique=len(np.unique(np.round(cent,10),axis=0))==len(cn)
 bounds=np.array([xyz.min(0),xyz.max(0)]);boundaries={}
 for name,g in z.items():
  if not isinstance(g,h5py.Group) or 'ElementConnectivity' not in g or int(g[' data'][0])!=7:continue
  v=xyz[g['ElementConnectivity/ data'][...].reshape(-1,4)-1];span=v.max(1)-v.min(1)
  dd={}
  for a in range(3):
   for side,t in [('min',bounds[0,a]),('max',bounds[1,a])]:
    mask=np.max(abs(v[:,:,a]-t),axis=1)<1e-8
    if mask.any():dd['XYZ'[a]+side]={'faces':int(mask.sum()),'area_m2':float(np.prod(span[mask][:,[b for b in range(3) if b!=a]],axis=1).sum())}
  boundaries[name]=dd
 alpha=z['Solution00001/VolumeFractionwater/ data'][...];water=float(volumes@alpha)
 required={'DOMAIN.inlet':'Xmin','DOMAIN.outlet':'Xmax','DOMAIN.span_source':'Ymin','DOMAIN.span_target':'Ymax','DOMAIN.bottom':'Zmin','DOMAIN.top':'Zmax'}
 bc_ok=all(set(boundaries.get(k,{}))=={v} for k,v in required.items()) and len(boundaries)==6
 single=bool(np.allclose(lo[:,1],20,atol=1e-10) and np.allclose(hi[:,1],20.02,atol=1e-10))
 volok=abs(float(volumes.sum())-48)<1e-8
 valid=bc_ok and single and volok and bool(corners) and unique and float(volumes.min())>0
 out={'case':p.name,'updated_at':datetime.datetime.now().astimezone().isoformat(),'cells':len(cn),'CGNS_cell_type':'HEXA_8','bounds':bounds.tolist(),'boundaries':boundaries,'boundary_mapping_valid':bc_ok,'single_span':single,'cells_touching_both_span_planes':int(sum(np.isclose(lo[:,1],20)&np.isclose(hi[:,1],20.02))),'orthogonal_hexahedra':bool(corners),'unique_cell_boxes':unique,'min_cell_volume_m3':float(volumes.min()),'sum_cell_volume_m3':float(volumes.sum()),'expected_domain_volume_m3':48,'volume_match':volok,'water_volume_m3':water,'mean_eta_from_volume_m':water/(80*.02)-24,'status':'geometry_pass' if valid else 'geometry_review_required'}
 (p/'topology_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
