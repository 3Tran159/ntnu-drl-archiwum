import os,sys,json
from pathlib import Path
for k in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"]:os.environ[k]="1"
sys.path.insert(0,r"F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
import h5py,numpy as np
P=Path(r"E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M09_mesh_r1")
R=Path(r"F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
with h5py.File(P/"mesh_star_export.CGNS","r") as f:
 z=f["Base/fluid"];xyz=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XZ"])
 g=z["Q2D_span_source"];off=g["ElementStartOffset/ data"][...];con=g["ElementConnectivity/ data"][...]-1
 polys=[];bounds=[]
 for i in range(len(off)-1):
  q=xyz[con[off[i]:off[i+1]]];lo=q.min(axis=0);hi=q.max(axis=0)
  if hi[1]>1.7 and lo[1]<2.3:polys.append(q);bounds.append([*lo,*hi])
 b=np.array(bounds)
 def intervals(axis,value):
  # Half-open intersection avoids counting a vertex twice.
  ids=np.where((b[:,axis]<=value)&(b[:,axis+2]>value))[0];out=[]
  for i in ids:
   q=polys[i];c=[]
   for u,v in zip(q,np.roll(q,-1,axis=0)):
    if min(u[axis],v[axis])<=value<max(u[axis],v[axis]):
     c.append(u[1-axis]+(value-u[axis])/(v[axis]-u[axis])*(v[1-axis]-u[1-axis]))
   c=sorted(c)
   for lo,hi in zip(c[::2],c[1::2]):
    if hi-lo>1e-12:out.append([float(lo),float(hi)])
  return out
 def stats(iv,lo,hi):
  v=[(a,b) for a,b in iv if b>lo+1e-10 and a<hi-1e-10]
  lengths=np.array([b-a for a,b in v]);covered=sum(min(b,hi)-max(a,lo) for a,b in v)
  return dict(crossed_cells=len(v),coverage_m=covered,full_intersection_length_m=dict(min=float(lengths.min()),median=float(np.median(lengths)),p95=float(np.quantile(lengths,.95)),max=float(lengths.max())))
 vertical=[]
 for x in [-30,-15,-12,-10,-5,-1,.01,.3,.6,.9,1.18,2,5,10,20,25,30,32,40]:
  iv=intervals(0,x);vertical.append(dict(x_m=x,band_1p7_to_2p3=stats(iv,1.7,2.3),wave_height_1p76_to_2p26=stats(iv,1.76,2.26)))
 horizontal=[]
 for z in [1.75,1.9,2.0,2.1,2.25]:
  iv=intervals(1,z);horizontal.append(dict(z_m=z,core=stats(iv,-15,25),foil_above=stats(iv,0,1.19)))
 result=dict(scope="Exact straight-line intersections with source-span CGNS polygons; crossed counts include cells partially covering each requested interval.",vertical=vertical,horizontal=horizontal)
 (R/"professor_c01_free_surface_ray_resolution.json").write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
