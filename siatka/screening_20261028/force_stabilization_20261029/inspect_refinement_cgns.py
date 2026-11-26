import sys
from pathlib import Path
sys.path.insert(0,'F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311')
import h5py,numpy as np
p=Path('F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/M06_build/mesh.CGNS')
with h5py.File(p) as f:
 z=f['Base/fluid']
 print('ZONE DATA',z[' data'][...].tolist(),'keys',list(z))
 for n,g in z.items():
  if isinstance(g,h5py.Group):
   print(n,dict(g.attrs),'keys',list(g))
   for k in [' data','ElementRange/ data','ElementConnectivity/ data','ElementStartOffset/ data']:
    if k in g:print(' ',k,g[k].shape,g[k].dtype,g[k][...].tolist() if g[k].size<12 else 'array')
 if 'ZoneBC' in z:
  for n,g in z['ZoneBC'].items():
   if isinstance(g,h5py.Group):
    print('BC',n,dict(g.attrs),list(g))
    for nn,gg in g.items():
     if isinstance(gg,h5py.Group):print('  ',nn,dict(gg.attrs),list(gg),gg[' data'].shape if ' data' in gg else '')
 print('ROOT',dict(f.attrs),list(f))
