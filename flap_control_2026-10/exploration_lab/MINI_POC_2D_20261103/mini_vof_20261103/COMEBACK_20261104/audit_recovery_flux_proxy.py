"""Geometric cell-centred face-flux proxy. This is not STAR's mass residual."""
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/"recovery_v3_deps"))
sys.path.insert(0,str(HERE/"WALL_FUNCTIONS_AUDIT"))
from scipy.spatial import cKDTree
from audit_wall import load_mesh, centroid
from audit_motion_map import signed_area
from summarize_h010 import field,col

mesh=HERE/"WALL_FUNCTIONS_AUDIT/RECOVERY_V2_TE_PARTIAL/geometry_and_mesh.msh"
xy,cells,wall=load_mesh(mesh)
center=np.array([centroid(xy[list(cell)]) for cell in cells])
area=np.array([signed_area(xy[list(cell)]) for cell in cells])
edges={}
for i,cell in enumerate(cells):
    for u,v in zip(cell,cell[1:]+cell[:1]):
        key=tuple(sorted((u,v)))
        edges.setdefault(key,[]).append((i,u,v))
inlet=[]
face=[]
for value in edges.values():
    i,u,v=value[0]
    if len(value)==2:
        face.append((i,value[1][0],u,v))
    elif np.allclose(xy[[u,v],0],-12):
        inlet.append((i,u,v))

def inspect(path):
    n,a=field(path)
    xyz=a[:,[col(n,"X ("),col(n,"Y (")]]
    volumes=a[:,col(n,"Volume (")]/.02
    dist,idx=cKDTree(xyz).query(center,k=8)
    mismatch=np.abs(volumes[idx]/area[:,None]-1)
    order=(dist/(np.sqrt(area)[:,None])+40*mismatch).argmin(axis=1)
    idx=idx[np.arange(len(center)),order]
    if len(set(idx))<.999*len(idx):
        raise ValueError("Native cell-coordinate association not one-to-one")
    v=a[idx][:,[col(n,"Velocity[i]"),col(n,"Velocity[j]")]]
    i,j,u,w=np.array(face).T
    t=xy[w]-xy[u]
    mid=(xy[u]+xy[w])*.5
    d1=np.linalg.norm(mid-center[i],axis=1)
    d2=np.linalg.norm(mid-center[j],axis=1)
    uf=(d2[:,None]*v[i]+d1[:,None]*v[j])/(d1+d2)[:,None]
    f=uf[:,0]*t[:,1]-uf[:,1]*t[:,0]
    net=np.bincount(i,weights=f,minlength=len(area))-np.bincount(j,weights=f,minlength=len(area))
    gross=np.bincount(i,weights=np.abs(f),minlength=len(area))+np.bincount(j,weights=np.abs(f),minlength=len(area))
    select=(center[:,0]>-.25)&(center[:,0]<1.55)&(np.abs(center[:,1])<.25)
    imbalance=np.abs(net[select])/np.maximum(gross[select],1e-15)
    out=dict(path=str(path),cells_in_box=int(select.sum()),unique_cell_matches=len(set(idx)),
             relative_flux_proxy_p50_p95_p99=np.quantile(imbalance,[.5,.95,.99]).tolist())
    return out

for p in sys.argv[1:]:
    print(json.dumps(inspect(Path(p))))

