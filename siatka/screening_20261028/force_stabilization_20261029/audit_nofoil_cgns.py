"""Independent no-foil CGNS audit. Compact records; does not modify simulations."""
import sys,json,datetime
from pathlib import Path
sys.path.insert(0,r'F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\deps311')
import h5py,numpy as np
p=Path(sys.argv[1]).resolve()
assert p.parent==Path('E:/ntnu/quasi2d_waves_20261029').resolve()
with h5py.File(p/'mesh.CGNS','r') as probe:
 is_hex=int(probe['Base/fluid/fluid/ data'][0])==17
if is_hex:
 import runpy
 runpy.run_path(str(Path(__file__).with_name('audit_hex_nofoil_cgns.py')),run_name='__main__');sys.exit(0)
with h5py.File(p/'mesh.CGNS','r') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 faces={};groups={};volflux={};areas={};onplane={}
 lo=xyz.min(0);hi=xyz.max(0)
 for name,g in z.items():
  if not isinstance(g,h5py.Group) or 'ElementConnectivity' not in g or int(g[' data'][0])!=22:continue
  off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0]);groups[name]=[]
  for i in range(len(off)-1):
   fi=start+i;v=con[off[i]:off[i+1]];faces[fi]=v;groups[name].append(fi);q=xyz[v]
   n=np.cross(q[1:-1]-q[0],q[2:]-q[0])*.5;ct=(q[0]+q[1:-1]+q[2:])/3
   volflux[fi]=float(np.sum(n*ct)/3);areas[fi]=float(np.linalg.norm(n.sum(0)))
   onplane[fi]=next(('XYZ'[a]+side for a in range(3) for side,t in [('min',lo[a]),('max',hi[a])] if np.max(abs(q[:,a]-t))<1e-8),'other')
 out={'case':p.name,'updated_at':datetime.datetime.now().astimezone().isoformat(),'bounds':np.array([lo,hi]).tolist(),'unique_y_count':len(np.unique(np.round(xyz[:,1],9))),'boundaries':{}}
 for name,ids in groups.items():
  if name.startswith('Polyfaces'):continue
  d={}
  for fi in ids:
   t=onplane[fi];r=d.setdefault(t,{'faces':0,'area_m2':0.});r['faces']+=1;r['area_m2']+=areas[fi]
  out['boundaries'][name]=d
 cg=z['fluid'];co=cg['ElementConnectivity/ data'][...];off=cg['ElementStartOffset/ data'][...];vol=[];single=0
 for i in range(len(off)-1):
  fs=co[off[i]:off[i+1]];tags=[onplane[abs(fi)] for fi in fs]
  single+=('Ymin' in tags and 'Ymax' in tags)
  vol.append(sum(volflux[abs(fi)]*(1 if fi>0 else -1) for fi in fs))
 volumes=np.abs(np.array(vol));a=z['Solution00001/VolumeFractionwater/ data'][...];w=float(volumes@a)
 expected=float(np.prod(hi-lo));planes={t:sum(r.get(t,{}).get('area_m2',0) for r in out['boundaries'].values()) for t in ['Xmin','Xmax','Ymin','Ymax','Zmin','Zmax','other']}
 expected_boundaries={'DOMAIN.inlet':'Xmin','DOMAIN.outlet':'Xmax','DOMAIN.span_source':'Ymin','DOMAIN.span_target':'Ymax','DOMAIN.bottom':'Zmin','DOMAIN.top':'Zmax'}
 boundary_ok=all(set(out['boundaries'].get(k,{}))=={v} for k,v in expected_boundaries.items()) and len(out['boundaries'])==6
 volume_ok=abs(volumes.sum()-expected)<expected*1e-7
 out.update(cells=len(vol),cells_touching_both_span_planes=single,single_span=single==len(vol),min_cell_volume_m3=float(volumes.min()),nonpositive_raw_cell_volume_count=int(sum(np.array(vol)<=0)),sum_cell_volume_m3=float(volumes.sum()),expected_domain_volume_m3=expected,volume_match=bool(volume_ok),water_volume_m3=w,mean_eta_from_volume_m=w/((hi[0]-lo[0])*(hi[1]-lo[1]))-24,boundary_area_by_plane=planes,boundary_mapping_valid=boundary_ok,status='geometry_pass' if boundary_ok and volume_ok and single==len(vol) else 'geometry_review_required')
 (p/'topology_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
