import sys,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';out=Q/'M04/repair_oriented_extrusion';out.mkdir(exist_ok=True)
sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py
target=out/'mesh_oriented_extrusion.CGNS'
if target.exists():raise RuntimeError('Preserve earlier attempt')
shutil.copy2(Q/'M04/repair_exact_extrusion/mesh_exact_extrusion.CGNS',target)
with h5py.File(target,'r+') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 faces={};groups={};ref={}
 for name,g in z.items():
  if isinstance(g,h5py.Group) and 'ElementConnectivity' in g and int(g[' data'][0])==22:
   off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0])
   groups[name]=(off,con,start)
   for i in range(len(off)-1):faces[start+i]=con[off[i]:off[i+1]];ref[start+i]=(name,i)
 count=max(faces)+1
 centers=np.zeros((count,3));area=np.zeros((count,3))
 for face,v in faces.items():
  pts=xyz[v];centers[face]=pts.mean(axis=0)
  area[face]=np.sum(np.cross(pts[1:-1]-pts[0],pts[2:]-pts[0]),axis=0)*.5
 co=z['fluid/ElementConnectivity/ data'][...];off=z['fluid/ElementStartOffset/ data'][...]
 srcids=set(range(groups['Q2D_span_source'][2],groups['Q2D_span_source'][2]+len(groups['Q2D_span_source'][0])-1))
 owners={};signs=np.zeros_like(co);volumes=[];closures=[];flips={};badinternal=[]
 for ci in range(len(off)-1):
  inds=np.arange(off[ci],off[ci+1]);ff=np.abs(co[inds]);src=[int(k) for k in ff if k in srcids];assert len(src)==1
  pp=xyz[faces[src[0]]];cc=pp.mean(axis=0);cc[1]=.02
  dot=np.einsum('ij,ij->i',area[ff],centers[ff]-cc);ss=np.where(dot>=0,1,-1)
  for idx,face,sgn in zip(inds,ff,ss):
   face=int(face)
   if face in owners:
    if owners[face][1]==sgn:badinternal.append(face)
   else:owners[face]=(ci,int(sgn));flips[face]=int(sgn)
   signs[idx]=int(sgn)
  outward=area[ff]*ss[:,None]
  closures.append(float(np.linalg.norm(outward.sum(axis=0))/np.linalg.norm(outward,axis=1).sum()))
  volumes.append(float(np.einsum('ij,ij->',outward,centers[ff]-cc)/3))
 result={'cells':len(volumes),'same_side_internal_faces':len(badinternal),'max_relative_cell_closure':max(closures),'negative_or_zero_reconstructed_volumes':int((np.array(volumes)<=0).sum()),'minimum_reconstructed_volume_m3':min(volumes),'reoriented_faces':sum(v<0 for v in flips.values()),'bad_face_ids':badinternal[:20]}
 (out/'geometry_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 if badinternal or max(closures)>1e-8 or min(volumes)<=0:raise RuntimeError('Geometric overlap or closure failure; do not import')
 for name,(offset,connect,start) in groups.items():
  updated=connect.copy()
  for i in range(len(offset)-1):
   if flips[start+i]<0:updated[offset[i]:offset[i+1]]=updated[offset[i]:offset[i+1]][::-1]
  z[name+'/ElementConnectivity/ data'][...]=updated+1
 newco=np.array([int(face)*int(sgn)*flips[int(face)] for face,sgn in zip(np.abs(co),signs)],dtype=co.dtype)
 z['fluid/ElementConnectivity/ data'][...]=newco
shutil.copy2(Q/'M04/mesh.sim',out/'input_invalid_copy.sim')
macro=(R/'ImportExactM04.java').read_text().replace('ImportExactM04','ImportOrientedM04').replace('M04/repair_exact_extrusion','M04/repair_oriented_extrusion').replace('mesh_exact_extrusion.CGNS','mesh_oriented_extrusion.CGNS')
(R/'ImportOrientedM04.java').write_text(macro)
(R/'m04_oriented_job.json').write_text(json.dumps({'source':str(out/'input_invalid_copy.sim'),'macro':str(R/'ImportOrientedM04.java'),'log':str(out/'import.log'),'np':2,'timeout_s':1800}))
