import sys,json
from pathlib import Path
sys.path.insert(0,r'F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\deps311')
import h5py,numpy as np
p=Path(r'E:\ntnu\quasi2d_waves_20261029\W20_H24_X4_Q2D_r2')
with h5py.File(p/'mesh.CGNS','r') as f:
 z=f['Base/fluid']; xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
 print(json.dumps({'bounds':np.array([xyz.min(0),xyz.max(0)]).tolist(),'zone_keys':list(z.keys()),'node_count':len(xyz)},indent=2))
 for name,g in z.items():
  if isinstance(g,h5py.Group):
   if 'ElementConnectivity' in g:
    print(name,'type',g[' data'][...].tolist(),'range',g['ElementRange/ data'][...].tolist())
   elif 'GridLocation' in g:print('solution',name,list(g.keys()))
