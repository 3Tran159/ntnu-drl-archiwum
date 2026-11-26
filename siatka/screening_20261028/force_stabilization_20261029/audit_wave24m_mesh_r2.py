import sys,json,collections
from pathlib import Path
sys.path.insert(0,r'F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\deps311')
import h5py,numpy as np
p=Path(r'E:\ntnu\quasi2d_waves_20261029\W20_H24_X4_Q2D_r2')
with h5py.File(p/'mesh.CGNS','r') as f:
 z=f['Base/fluid']; xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 faces={};groups={};orient={};geom={}
 for name,g in z.items():
  if not isinstance(g,h5py.Group) or 'ElementConnectivity' not in g or int(g[' data'][0])!=22:continue
  off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0]);groups[name]=[]
  for i in range(len(off)-1):
   fi=start+i;v=con[off[i]:off[i+1]];faces[fi]=v;groups[name].append(fi)
   q=xyz[v];n=np.sum(np.cross(q,np.roll(q,-1,axis=0)),axis=0)*.5
   cent=q.mean(0);orient[fi]=int(np.argmax(abs(n)));geom[fi]=(cent,n)
 out={'bounds':np.array([xyz.min(0),xyz.max(0)]).tolist(),'unique_y':np.unique(np.round(xyz[:,1],9)).tolist(),'boundary_groups':{}}
 for name,ids in groups.items():
  if name.startswith('Polyfaces'):continue
  d={}
  for fi in ids:
   cent,n=geom[fi];axis=orient[fi];k='XYZ'[axis]+'='+str(round(float(cent[axis]),6));r=d.setdefault(k,{'faces':0,'area_m2':0.,'bounds_min':[float('inf')]*3,'bounds_max':[-float('inf')]*3})
   r['faces']+=1;r['area_m2']+=float(np.linalg.norm(n));r['bounds_min']=np.minimum(r['bounds_min'],xyz[faces[fi]].min(0)).tolist();r['bounds_max']=np.maximum(r['bounds_max'],xyz[faces[fi]].max(0)).tolist()
  out['boundary_groups'][name]=d
 cg=z['fluid'];co=cg['ElementConnectivity/ data'][...];off=cg['ElementStartOffset/ data'][...]
 n=0;vol=[];volalpha=0.;alpha=z['Solution00001/VolumeFractionwater/ data'][...]
 for i in range(len(off)-1):
  fs=co[off[i]:off[i+1]];ys=[]
  for fi in fs:
   cent,no=geom[abs(fi)]
   if orient[abs(fi)]==1:ys.append(cent[1])
  if any(abs(a-20)<1e-8 for a in ys) and any(abs(a-20.02)<1e-8 for a in ys):n+=1
  volume=abs(sum(np.dot(geom[abs(fi)][0],geom[abs(fi)][1])*(1 if fi>0 else -1) for fi in fs)/3);vol.append(volume);volalpha+=volume*float(alpha[i])
 out.update(cells=len(off)-1,cells_touching_both_span_planes=n,single_span=n==len(off)-1,min_cell_volume_m3=min(vol),sum_cell_volume_m3=sum(vol),water_volume_m3=volalpha,expected_domain_volume_m3=80*30*.02,mean_eta_from_volume_m=volalpha/(80*.02)-24)
 out['status']='needs_boundary_review'
 (p/'independent_geometry_audit.json').write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))
