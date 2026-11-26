from pathlib import Path
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT.parent / "tools" / "deps"))
import gmsh

HINGE = np.array([.952, .02128173276777])
BLEND = .035
RIGID_RADIUS = .30
OUTER_RADIUS = 1.40

def s5(x):
    q = np.clip(x, 0, 1)
    return q**3 * (10 - 15*q + 6*q*q)

def signed_area(points):
    nxt = np.roll(points, -1, axis=-2)
    return .5 * np.sum(points[...,0] * nxt[...,1] - points[...,1] * nxt[...,0], axis=-1)

def map_vertices(xy, deg):
    shifted = xy - HINGE
    w = s5(shifted[:,0] / BLEND) * s5((OUTER_RADIUS - np.linalg.norm(shifted, axis=1)) / (OUTER_RADIUS - RIGID_RADIUS))
    t = np.radians(deg) * w
    c, s = np.cos(t), np.sin(t)
    x, y = shifted.T
    return HINGE + np.column_stack([c*x + s*y, -s*x + c*y])

def mesh():
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(ROOT / "mini_vof_20261103" / "SEALED0_A005" / "geometry_and_mesh.msh"))
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xy = np.array(xyz).reshape(-1,3)[:,:2]
        idx = {int(tag): i for i, tag in enumerate(tags)}
        groups = []
        for kind, _, nodes in zip(*gmsh.model.mesh.getElements(2)):
            n = {2: 3, 3: 4}[kind]
            groups.append(np.array([idx[int(tag)] for tag in nodes]).reshape(-1,n))
        boundaries = {}
        for dim, tag in gmsh.model.getPhysicalGroups(1):
            name = gmsh.model.getPhysicalName(dim, tag)
            ids = {idx[int(v)] for c in gmsh.model.getEntitiesForPhysicalGroup(dim, tag) for a in gmsh.model.mesh.getElements(1,c)[2] for v in a}
            boundaries[name] = np.array(sorted(ids))
        return xy, groups, boundaries
    finally:
        gmsh.finalize()

def main():
    xy, groups, bounds = mesh()
    aft = bounds["flap"][xy[bounds["flap"],0] >= HINGE[0] + BLEND]
    base = [signed_area(xy[g]) for g in groups]
    assert all(np.all(a>0) for a in base)
    angles = np.linspace(-2,2,41)
    out = []
    for angle in angles:
        new = map_vertices(xy, angle)
        areas = [signed_area(new[g]) for g in groups]
        moved_main = np.max(np.linalg.norm(new[bounds["main"]]-xy[bounds["main"]], axis=1))
        moved_outer = max(np.max(np.linalg.norm(new[bounds[k]]-xy[bounds[k]], axis=1)) for k in ("inlet","outlet","top","bottom"))
        old_vec = xy[aft] - HINGE
        new_vec = new[aft] - HINGE
        cross = old_vec[:,0]*new_vec[:,1] - old_vec[:,1]*new_vec[:,0]
        actual = -np.degrees(np.arctan2(cross, np.sum(old_vec*new_vec, axis=1)))
        out.append(dict(target_deg=float(angle), max_aft_angle_error_deg=float(max(abs(actual-angle))),
                        main_displacement_m=float(moved_main), outer_displacement_m=float(moved_outer),
                        min_volume_m3=float(min(a.min() for a in areas)*.02),
                        min_area_ratio=float(min((a/b).min() for a,b in zip(areas,base))),
                        max_area_ratio=float(max((a/b).max() for a,b in zip(areas,base))),
                        nonpositive_cells=int(sum((a<=0).sum() for a in areas))))
    ok = all(r["nonpositive_cells"] == 0 and r["main_displacement_m"] < 1e-12 and
             r["outer_displacement_m"] < 1e-12 and r["max_aft_angle_error_deg"] < 1e-8 for r in out)
    data = dict(status="OFFLINE_MAP_PASS" if ok else "HOLD", native_motion_verified=False,
                cells=sum(len(g) for g in groups), span_m=.02, main_vertices=len(bounds["main"]),
                rigid_flap_vertices=len(aft), seam_x_m=HINGE[0], blend_m=BLEND,
                case="SEALED, zero gap, deforms a 35-mm strip aft of the hinge",
                min_volume_m3=min(r["min_volume_m3"] for r in out),
                min_area_ratio=min(r["min_area_ratio"] for r in out), angles=out)
    (HERE / "MOTION_OFFLINE.json").write_text(json.dumps(data,indent=2),encoding="utf8")
    for k in ["status","cells","rigid_flap_vertices","min_volume_m3","min_area_ratio"]:
        print(k,data[k])
    if not ok:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
