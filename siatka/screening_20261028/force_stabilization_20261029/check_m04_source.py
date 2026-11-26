import sys,json
from pathlib import Path
Q=Path('F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029');sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py
with h5py.File(Q/'M04/mesh.CGNS') as f:
 z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 g=z['Q2D_span_source'];off=g['ElementStartOffset/ data'][...];con=g['ElementConnectivity/ data'][...]-1;start=int(g['ElementRange/ data'][0])
 ar=[]
 for i in range(len(off)-1):
  pp=xyz[con[off[i]:off[i+1]]][:,[0,2]];ar.append(.5*np.sum(pp[:,0]*np.roll(pp[:,1],-1)-np.roll(pp[:,0],-1)*pp[:,1]))
 ar=np.array(ar);bad=np.where(ar*np.sign(np.median(ar))<=0)[0]
 co=z['fluid/ElementConnectivity/ data'][...]
 print('NFACE signed references',int((co<0).sum()),int((co>0).sum()),'median area sign',np.sign(np.median(ar)))
 for i in bad:
  p=xyz[con[off[i]:off[i+1]]][:,[0,2]]
  print(json.dumps({'face':int(start+i),'centroid':p.mean(axis=0).tolist(),'signed_area':ar[i],'verts':p.tolist()}))
