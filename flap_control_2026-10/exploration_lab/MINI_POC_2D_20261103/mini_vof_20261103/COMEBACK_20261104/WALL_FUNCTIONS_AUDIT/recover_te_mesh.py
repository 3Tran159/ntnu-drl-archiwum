"""Restore locally the pre-V2 wake geometry while retaining the foil and VOF grid."""
import json
from pathlib import Path
import time

import numpy as np
from audit_wall import CB, HERE, ROOT, load_mesh
from audit_motion_map import s5
from prepare_high_yplus_v2 import check
from run_day import sha

BASE = CB.parent/"SEALED0_A005"/"geometry_and_mesh.msh"
V2 = HERE/"HIGH_YPLUS_CANDIDATE_V2"/"geometry_and_mesh.msh"
OUT = HERE/"RECOVERY_V2_TE_LOCAL"
HOTSPOTS = (7449,)

def metrics(points):
    edges = np.linalg.norm(np.roll(points,-1,axis=1)-points,axis=2)
    p = points-points[:,:1]
    q = np.roll(p,-1,axis=1)
    area = .5*np.sum(p[:,:,0]*q[:,:,1]-p[:,:,1]*q[:,:,0],axis=1)
    return area, 2*area/edges.max(axis=1)

def main():
    started = time.perf_counter()
    if OUT.exists():
        raise FileExistsError(OUT)
    old, cells, walls = load_mesh(BASE)
    v2, current_cells, current_walls = load_mesh(V2)
    if cells!=current_cells or walls!=current_walls:
        raise ValueError("Pre-V2 and V2 connectivity do not match")
    weight = s5((old[:,0]-1.11)/.05)
    adjusted = v2 + weight[:,None]*(old-v2)
    changed = np.linalg.norm(adjusted-v2,axis=1)>1e-12
    foil_nodes = np.array(sorted({v for a,b,_ in walls for v in (a,b)}))
    if np.any(changed[foil_nodes]) or np.any(changed & (old[:,1]>=1.621)):
        raise ValueError("Protected foil or free-surface strip changed")
    trials = check(adjusted,cells)
    if any(row["nonpositive_cells_or_corners"] for row in trials):
        raise ValueError("Nonpositive cells or corners through motion range")
    areas = []
    for n in (3,4):
        group = np.array([c for c in cells if len(c)==n])
        area, _ = metrics(adjusted[group])
        areas.append(float(area.min()))
    hotspots=[]
    for i in HOTSPOTS:
        group = np.array([cells[i]])
        av2,hv2 = metrics(v2[group])
        anew,hnew = metrics(adjusted[group])
        hotspots.append(dict(cell_order_0based=i,old_height_um=float(hv2[0]*1e6),
            new_height_um=float(hnew[0]*1e6),old_area_m2=float(av2[0]),new_area_m2=float(anew[0])))
    import gmsh
    OUT.mkdir()
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal",0)
        gmsh.open(str(V2))
        tags,p,_ = gmsh.model.mesh.getNodes()
        if not np.array_equal(np.array(p).reshape(-1,3)[:,:2],v2):
            raise ValueError("Unexpected node order")
        for i in np.flatnonzero(changed):
            gmsh.model.mesh.setNode(int(tags[i]),[*adjusted[i],0.],[])
        gmsh.write(str(OUT/"geometry_and_mesh.msh"))
    finally:
        gmsh.finalize()
    audit=dict(status="OFFLINE_MESH_MOTION_PASS",source_v2=str(V2),source_v2_sha256=sha(V2),
        original_mesh_sha256=sha(BASE),cells=len(cells),vertices_moved=int(changed.sum()),
        x_changed_m=[float(old[changed,0].min()),float(old[changed,0].max())],
        y_changed_m=[float(old[changed,1].min()),float(old[changed,1].max())],
        foil_vertices_changed=0,vof_corridor_vertices_changed=0,min_area_m2=min(areas),
        hotspot_cells=hotspots,kinematic_grid_check=trials)
    meta=json.loads((V2.parent/"mesh_metadata.json").read_text(encoding="utf8"))
    (OUT/"mesh_metadata.json").write_text(json.dumps({**meta,**audit},indent=2),encoding="utf8")
    script=ROOT/"extrude_foil_vof.py"
    src=script.read_text(encoding="utf8").replace("R=Path(__file__).resolve().parent",f"R=Path({str(ROOT)!r})")
    tag="D=R/'mini_vof_20261103';src=D/'SEALED0_A005';o=D/'Q2D_SEALED0_CALM_PREPARED';"
    if src.count(tag)!=1:
        raise ValueError("Unexpected extrusion source")
    src=src.replace(tag,f"src=Path({str(OUT)!r});o=Path({str(OUT/'Q2D')!r});")
    exec(compile(src,str(script),"exec"),{"__file__":str(script)})
    mesh=OUT/"Q2D"/"mesh_3d.msh"
    audit.update(mesh=str(mesh),mesh_sha256=sha(mesh),offline_seconds=time.perf_counter()-started)
    (OUT/"RECOVERY_MESH_AUDIT.json").write_text(json.dumps(audit,indent=2),encoding="utf8")
    print(json.dumps({k:v for k,v in audit.items() if k!="kinematic_grid_check"},indent=2))

if __name__=="__main__":
    main()

