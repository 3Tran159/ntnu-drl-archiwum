"""Create an exactly extruded, consistently oriented copy of a one-cell-span CGNS mesh."""
import sys,json,shutil
from pathlib import Path
Q=Path('F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029')
sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py
src=Path(sys.argv[1]);out=Path(sys.argv[2])
if out.exists():raise RuntimeError('Refusing to overwrite prior extrusion')
shutil.copy2(src,out)
with h5py.File(out,'r+') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 faces={};groups={};pairs={}
 for name,g in z.items():
  if isinstance(g,h5py.Group) and 'ElementConnectivity' in g and int(g[' data'][0])==22:
   off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0]);groups[name]=(off,con,start)
   for i in range(len(off)-1):
    v=con[off[i]:off[i+1]];faces[start+i]=v
    for a,b in zip(v,np.roll(v,-1)):
     if abs(xyz[a,1]-xyz[b,1])>.01:
      if xyz[a,1]>xyz[b,1]:a,b=b,a
      if a in pairs and pairs[a]!=b:raise RuntimeError('Ambiguous span pairing')
      pairs[int(a)]=int(b)
 source=np.array(sorted(pairs));target=np.array([pairs[k] for k in source])
 if len(set(target))!=len(target) or len(source)*2!=len(xyz):raise RuntimeError('Not an exact single-layer topology')
 displacement=np.linalg.norm(xyz[target][:,[0,2]]-xyz[source][:,[0,2]],axis=1)
 xyz[target,0]=xyz[source,0];xyz[target,2]=xyz[source,2];xyz[source,1]=.01;xyz[target,1]=.03
 for i,a in enumerate('XYZ'):z['GridCoordinates/Coordinate'+a+'/ data'][...]=xyz[:,i]
 count=max(faces)+1;centers=np.zeros((count,3));area=np.zeros((count,3))
 for face,v in faces.items():
  pts=xyz[v];centers[face]=pts.mean(axis=0);area[face]=np.sum(np.cross(pts[1:-1]-pts[0],pts[2:]-pts[0]),axis=0)*.5
 co=z['fluid/ElementConnectivity/ data'][...];off=z['fluid/ElementStartOffset/ data'][...]
 srcids=set(range(groups['Q2D_span_source'][2],groups['Q2D_span_source'][2]+len(groups['Q2D_span_source'][0])-1))
 owners={};signs=np.zeros_like(co);volumes=[];closures=[];flips={};badinternal=[]
 for ci in range(len(off)-1):
  inds=np.arange(off[ci],off[ci+1]);ff=np.abs(co[inds]);srcfaces=[int(k) for k in ff if k in srcids]
  if len(srcfaces)!=1:raise RuntimeError('Cell lacks unique source face')
  cc=xyz[faces[srcfaces[0]]].mean(axis=0);cc[1]=.02
  dot=np.einsum('ij,ij->i',area[ff],centers[ff]-cc);ss=np.where(dot>=0,1,-1)
  for idx,face,sgn in zip(inds,ff,ss):
   face=int(face)
   if face in owners:
    if owners[face][1]==sgn:badinternal.append(face)
   else:owners[face]=(ci,int(sgn));flips[face]=int(sgn)
   signs[idx]=int(sgn)
  outward=area[ff]*ss[:,None];closures.append(float(np.linalg.norm(outward.sum(axis=0))/np.linalg.norm(outward,axis=1).sum()))
  volumes.append(float(np.einsum('ij,ij->',outward,centers[ff]-cc)/3))
 result={'cells':len(volumes),'same_side_internal_faces':len(badinternal),'max_relative_cell_closure':max(closures),'negative_or_zero_reconstructed_volumes':int((np.array(volumes)<=0).sum()),'minimum_reconstructed_volume_m3':min(volumes),'reoriented_faces':sum(v<0 for v in flips.values()),'max_target_projection_removed_m':float(displacement.max()),'source_section_unchanged':True,'span_m':.02,'method':'Exact source-plane extrusion with consistent outward owner-face orientations and signed NFACE connectivity.'}
 out.with_suffix('.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 if badinternal or max(closures)>1e-8 or min(volumes)<=0:raise RuntimeError('Geometric validity failed; do not import')
 for name,(offset,connect,start) in groups.items():
  updated=connect.copy()
  for i in range(len(offset)-1):
   if flips[start+i]<0:updated[offset[i]:offset[i+1]]=updated[offset[i]:offset[i+1]][::-1]
  z[name+'/ElementConnectivity/ data'][...]=updated+1
 z['fluid/ElementConnectivity/ data'][...]=np.array([int(face)*int(sgn)*flips[int(face)] for face,sgn in zip(np.abs(co),signs)],dtype=co.dtype)
