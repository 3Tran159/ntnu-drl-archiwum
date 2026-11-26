"""Candidate: move only near-wall nodes of a copy of the existing quad/tri mesh."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from audit_wall import HERE, CB, ROOT, C, load_mesh, wall_geometry, group_geometry
from audit_motion_map import map_vertices, s5
import gmsh

OUT=HERE/"HIGH_YPLUS_CANDIDATE"
SOURCE=CB.parent/"SEALED0_A005"/"geometry_and_mesh.msh"
CUTOFF=.030

def propose(xy,walls):
    new=xy.copy()
    edges=np.array([[a,b] for a,b,_ in walls])
    a=xy[edges[:,0]]
    t=xy[edges[:,1]]-a
    t2=(t*t).sum(axis=1)
    nodes=np.where((xy[:,0]>a[:,0].min()-CUTOFF)&(xy[:,0]<a[:,0].max()+CUTOFF)&
                   (xy[:,1]>a[:,1].min()-CUTOFF)&(xy[:,1]<a[:,1].max()+CUTOFF))[0]
    old=np.r_[0,np.cumsum(20e-6*1.2**np.arange(12)),CUTOFF]
    for ids in np.array_split(nodes,max(1,int(np.ceil(len(nodes)/128)))):
        rel=xy[ids,None,:]-a
        frac=np.clip(np.sum(rel*t,axis=2)/t2,0,1)
        offsets=rel-frac[:,:,None]*t
        sq=np.sum(offsets*offsets,axis=2)
        j=np.argmin(sq,axis=1)
        k=np.arange(len(ids))
        d=np.sqrt(sq[k,j])
        m=(d>1e-10)&(d<CUTOFF)
        x=(xy[ids,0]-offsets[k,j,0])/C
        # Keep the leading and trailing tips closer to the lower estimate.
        thickness=.00018+.00009*s5((x-.015)/.085)-.00007*s5((x-.96)/.04)
        thickness+=.00002*s5((x-.81)/.10)*(1-s5((x-.94)/.045))
        layer=np.r_[0,np.cumsum(1.12**np.arange(12))]
        new_depth=np.array([np.interp(dd,old,np.r_[h*layer,CUTOFF]) for dd,h in zip(d[m],thickness[m])])
        new[ids[m]]+=(new_depth/d[m]-1)[:,None]*offsets[k[m],j[m]]
    return new

def check(xy,cells):
    result=[]
    groups=[np.array([a for a in cells if len(a)==n]) for n in (3,4)]
    for angle in np.linspace(-2,2,41):
        x=map_vertices(xy,angle)
        volume=np.inf;jacobian=np.inf;bad=0
        for g in groups:
            p=x[g];rel=p-p[:,:1];nxt=np.roll(rel,-1,axis=1)
            vol=.01*np.sum(rel[:,:,0]*nxt[:,:,1]-rel[:,:,1]*nxt[:,:,0],axis=1)
            v=np.roll(p,-1,axis=1)-p
            w=np.roll(v,-1,axis=1)
            j=v[:,:,0]*w[:,:,1]-v[:,:,1]*w[:,:,0]
            volume=min(volume,float(vol.min()))
            jacobian=min(jacobian,float(j.min()))
            bad+=int(((vol<=0)|(j.min(axis=1)<=0)).sum())
        result.append(dict(angle_deg=float(angle),min_volume_m3=volume,min_corner_jacobian_m2=jacobian,
                           nonpositive_cells_or_corners=bad))
    return result

def main():
    start=time.perf_counter()
    OUT.mkdir(exist_ok=False)
    xy,cells,walls=load_mesh(SOURCE)
    new=propose(xy,walls)
    shifted=np.linalg.norm(new-xy,axis=1)>1e-13
    wall=np.array(sorted({v for a,b,_ in walls for v in (a,b)}))
    assert not np.any(shifted[wall])
    assert not np.any(shifted&(xy[:,1]>1.621))
    trials=check(new,cells)
    meta=dict(status="OFFLINE_MESH_MOTION_PASS" if all(a["nonpositive_cells_or_corners"]==0 for a in trials) else "HOLD_MESH",
              source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              cells=len(cells),nodes=len(xy),nodes_moved=int(shifted.sum()),wall_nodes_moved=0,
              vof_corridor_nodes_moved=0,redistribution_cutoff_m=CUTOFF,first_layer_design_m=[.00018,.00029],
              original_connectivity_preserved=True,first_layer_rows=12,target_internal_growth=1.12,
              kinematic_grid_check=trials,solver_started=False)
    if meta["status"]=="OFFLINE_MESH_MOTION_PASS":
        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal",0)
            gmsh.open(str(SOURCE))
            tags,p,_=gmsh.model.mesh.getNodes()
            assert np.array_equal(np.array(p).reshape(-1,3)[:,:2],xy)
            for j in np.where(shifted)[0]:
                gmsh.model.mesh.setNode(int(tags[j]),[float(new[j,0]),float(new[j,1]),0.],[])
            gmsh.write(str(OUT/"geometry_and_mesh.msh"))
        finally:
            gmsh.finalize()
        _,_,q=wall_geometry(OUT/"geometry_and_mesh.msh")
        meta["wall_geometry"]=group_geometry(q)
        original=json.loads((SOURCE.parent/"mesh_metadata.json").read_text(encoding="utf8"))
        (OUT/"mesh_metadata.json").write_text(json.dumps({**original,**meta},indent=2),encoding="utf8")
        src=(ROOT/"extrude_foil_vof.py").read_text(encoding="utf8")
        src=src.replace("R=Path(__file__).resolve().parent",f"R=Path({str(ROOT)!r})")
        old="D=R/'mini_vof_20261103';src=D/'SEALED0_A005';o=D/'Q2D_SEALED0_CALM_PREPARED';"
        if src.count(old)!=1:raise RuntimeError("Extrusion source contract changed")
        src=src.replace(old,f"src=Path({str(OUT)!r});o=Path({str(OUT/'Q2D')!r});")
        exec(compile(src,str(ROOT/"extrude_foil_vof.py"),"exec"),{"__file__":str(ROOT/"extrude_foil_vof.py")})
        meta["native_import_file"]=str(OUT/"Q2D"/"mesh_3d.msh")
        p=Path(meta["native_import_file"])
        meta["native_import_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
    meta["offline_wall_seconds"]=time.perf_counter()-start
    (OUT/"CANDIDATE_AUDIT.json").write_text(json.dumps(meta,indent=2,allow_nan=False),encoding="utf8")
    print(json.dumps({k:v for k,v in meta.items() if k not in ("wall_geometry","kinematic_grid_check")},indent=2))

if __name__=="__main__":main()

