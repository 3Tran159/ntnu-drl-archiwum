import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,r"F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
import h5py,numpy as np
P=Path(r"E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M09_mesh_r1")
R=Path(r"F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
src=P/"mesh_star_export.CGNS"
with h5py.File(src,"r") as f:
 z=f["Base/fluid"]
 xyz=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XYZ"])
 g=z["Q2D_span_source"]; off=g["ElementStartOffset/ data"][...]; con=g["ElementConnectivity/ data"][...]-1
 records=[]
 for i in range(len(off)-1):
  q=xyz[con[off[i]:off[i+1]]][:,[0,2]]
  lo=q.min(axis=0);hi=q.max(axis=0)
  if hi[1]<1.7 or lo[1]>2.3: continue
  area=abs(np.dot(q[:,0],np.roll(q[:,1],-1))-np.dot(q[:,1],np.roll(q[:,0],-1)))/2
  records.append([q[:,0].mean(),q[:,1].mean(),lo[0],hi[0],lo[1],hi[1],hi[0]-lo[0],hi[1]-lo[1],area])
 a=np.array(records)
 def summary(mask):
  v=a[mask]
  if not len(v):return {"cells":0}
  def stats(col):
   x=v[:,col];idx=np.argsort(x);c=np.cumsum(v[idx,8]);return dict(min=float(x.min()),median=float(np.median(x)),p95=float(np.quantile(x,.95)),max=float(x.max()),area_weighted_p95=float(x[idx[np.searchsorted(c,.95*c[-1])]]))
  dx=stats(6);dz=stats(7)
  return dict(cells=len(v),bbox_dx_m=dx,bbox_dz_m=dz,lambda20_over_dx_min=20/dx["max"],height0p5_over_dz_min=.5/dz["max"],area_fraction_dx_gt0p25=float(v[v[:,6]>.2500001,8].sum()/v[:,8].sum()),area_fraction_dz_gt0p025=float(v[v[:,7]>.0250001,8].sum()/v[:,8].sum()))
 zones={}
 cuts=[-35,-15,-11.9,-5,-2,0,2,5,10,20,25,30.94,45]
 for lo,hi in zip(cuts,cuts[1:]):
  zones[str(lo)+":"+str(hi)]=summary((a[:,0]>=lo-1e-8)&(a[:,0]<hi-1e-8))
 bands={}
 for lo,hi in zip([1.7,1.8,1.9,2.0,2.1,2.2],[1.8,1.9,2.0,2.1,2.2,2.3]):
  bands[str(lo)+":"+str(hi)]=summary((a[:,5]>lo+1e-8)&(a[:,4]<hi-1e-8)&(a[:,0]>-15)&(a[:,0]<25))
 w=z["HF_012_wall/ElementConnectivity/ data"][...]-1
 foil=xyz[np.unique(w)]
 result=dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),scope="Read-only projected cell-bounding-box free-surface resolution audit; no wave-grid validation",method="One source-span polygon per volume cell; all polygons intersecting z=1.7..2.3 m. Statistics grouped by arithmetic polygon-vertex x centroid. Bounding-box extents are reported, not directional edge lengths.",free_surface_band_m=[1.7,2.3],wave_height_m=.5,wavelength_m=20,foil_x_bounds_m=[float(foil[:,0].min()),float(foil[:,0].max())],all=summary(np.ones(len(a),dtype=bool)),core=summary((a[:,0]>-15)&(a[:,0]<25)),foil_above=summary((a[:,0]>foil[:,0].min())&(a[:,0]<foil[:,0].max())),x_bands=zones,core_z_bands=bands,nofoil_R5_reference=dict(dx_m=.2,dz_m=.025,cells_per_wavelength=100,cells_per_height=20),installed_guidance=dict(source="GUID-886FDC20-F60F-4875-8D46-109D27E6ED08",dx="lambda/80 to lambda/100",dz="about H/20",vertical_transition="avoid vertical resolution changes within wave zone"))
 (R/"professor_c01_free_surface_resolution.json").write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))
