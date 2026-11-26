import sys
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
sys.path.insert(0,str(root/"deps311"))
import h5py,numpy as np
f=h5py.File(root/"M01/mesh.CGNS")
def visit(n,o):
 if isinstance(o,h5py.Dataset):
  print(n,o.shape,o.dtype)
  if o.size<20:print(o[...])
f.visititems(visit)
