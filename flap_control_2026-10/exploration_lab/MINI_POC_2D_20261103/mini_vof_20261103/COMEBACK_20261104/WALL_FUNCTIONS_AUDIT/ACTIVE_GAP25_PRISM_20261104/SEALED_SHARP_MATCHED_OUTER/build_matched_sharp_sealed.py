from pathlib import Path
import ctypes
import hashlib
import json
import sys

import numpy as np

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parents[5] / "tools" / "deps"))
import gmsh

SOURCE = OUT.parents[6] / "hydro_validation_2606_20261102/geometry/gap_002500um/geometry.json"
H1 = 0.00018
THICKNESS = H1 * (1 + 1.18 + 1.18**2) + 1e-6
PROFILE_TOL = 0.000015

kernel = ctypes.WinDLL("kernel32")
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.SetProcessAffinityMask.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 16):
    raise RuntimeError("Could not pin meshing to the verified E-core")

g = json.loads(SOURCE.read_text())
hinge = np.array([g["hinge_x_m"], g["hinge_z_m"]])


def simplify(points):
    a, b = points[0], points[-1]
    edge = b - a
    fraction = np.clip((points - a) @ edge / (edge @ edge), 0, 1)
    error = np.linalg.norm(points - (a + fraction[:, None] * edge), axis=1)
    j = np.argmax(error)
    if error[j] <= PROFILE_TOL:
        return points[[0, -1]]
    return np.vstack([simplify(points[:j + 1])[:-1], simplify(points[j:])])


def solid(name):
    poly = np.array(g[name + "_polygon"])
    poly = poly[np.r_[True, np.linalg.norm(np.diff(poly, axis=0), axis=1) > 1e-8]]
    if np.linalg.norm(poly[-1] - poly[0]) < 1e-8:
        poly = poly[:-1]
    split = np.argmax(np.linalg.norm(poly - poly[0], axis=1))
    return np.vstack([simplify(poly[:split + 1])[:-1],
                      simplify(np.vstack([poly[split:], poly[:1]]))[:-1]])


def smooth(t):
    q = np.clip(t, 0, 1)
    return q**3 * (10 - 15*q + 6*q*q)


def weights(xy):
    x, y = (xy - hinge).T
    radius = np.hypot(x, y)
    return smooth(x/.035) * smooth((1.4 - radius)/1.1)


def move(xy, angle):
    x, y = (xy - hinge).T
    a = np.radians(angle) * weights(xy)
    return hinge + np.column_stack([x*np.cos(a) + y*np.sin(a), -x*np.sin(a) + y*np.cos(a)])


def cross(a, b):
    return a[..., 0]*b[..., 1] - a[..., 1]*b[..., 0]


def write_fluent(nodes, cells, boundary):
    faces = {}
    for cid, cell in enumerate(cells, 1):
        for a, b in zip(cell, cell[1:] + cell[:1]):
            key = tuple(sorted((a, b)))
            if key in faces:
                assert faces[key][3] == 0
                faces[key][3] = cid
            else:
                faces[key] = [a + 1, b + 1, cid, 0]
    zones = {name: [] for name in ("interior", "main", "flap", "inlet", "outlet", "top", "bottom")}
    for key, face in faces.items():
        zones["interior" if face[3] else boundary[key]].append(face)
    types = {"interior": (2, "interior"), "main": (3, "wall"), "flap": (3, "wall"),
             "inlet": (10, "velocity-inlet"), "outlet": (5, "pressure-outlet"), "top": (7, "symmetry"), "bottom": (7, "symmetry")}
    with (OUT / "mesh_2d.msh").open("x", encoding="ascii") as f:
        f.write(f'(0 "Sharp sealed flap with wall-layer quadrilaterals")\n(2 2)\n(10 (0 1 {len(nodes):x} 0 2))\n(10 (1 1 {len(nodes):x} 1 2)(\n')
        f.writelines(f"{x:.15g} {y:.15g}\n" for x, y in nodes)
        f.write(f"))\n(12 (0 1 {len(cells):x} 0))\n(12 (1 1 {len(cells):x} 1 0)(\n")
        f.write(" ".join("1" if len(c) == 3 else "3" for c in cells))
        f.write(f"\n))\n(13 (0 1 {len(faces):x} 0))\n")
        first = 1
        for zid, (name, fs) in enumerate(zones.items(), 2):
            code, label = types[name]
            last = first + len(fs) - 1
            f.write(f"(13 ({zid:x} {first:x} {last:x} {code:x} 2)(\n")
            f.writelines(" ".join(f"{v:x}" for v in face) + "\n" for face in fs)
            f.write(f"))\n(45 ({zid} {label} {name})())\n")
            first = last + 1
        f.write("(45 (1 fluid MINI_water)())\n")



SEALED = OUT.parents[1]/"COARSE_FACETED_OPEN_CELLS"/"geometry_and_mesh.msh"


def reference_mesh():
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Verbosity", 2)
        gmsh.open(str(SEALED))
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xy = xyz.reshape(-1,3)[:,:2]
        lookup = {int(t):i for i,t in enumerate(tags)}
        cells=[]
        for kind,_,conn in zip(*gmsh.model.mesh.getElements(2)):
            count={2:3,3:4}[kind]
            cells.extend(np.array([lookup[int(t)] for t in conn]).reshape(-1,count).tolist())
        boundary={}
        for dim,group in gmsh.model.getPhysicalGroups(1):
            name=gmsh.model.getPhysicalName(dim,group)
            for curve in gmsh.model.getEntitiesForPhysicalGroup(dim,group):
                for conn in gmsh.model.mesh.getElements(1,curve)[2]:
                    for a,b in conn.reshape(-1,2):
                        boundary[tuple(sorted((lookup[int(a)],lookup[int(b)])))]=name
        return xy,cells,boundary
    finally:
        gmsh.finalize()


def cavity(xy,cells,boundary):
    removed=[]
    kept=[]
    low=np.array([-.11,-.13])
    high=np.array([1.32,.19])
    for cell in cells:
        p=xy[cell]
        if np.all(p.max(axis=0)>=low) and np.all(p.min(axis=0)<=high):
            removed.append(cell)
        else:
            kept.append(cell)
    exposed=set()
    for cell in removed:
        for a,b in zip(cell,cell[1:]+cell[:1]):
            key=tuple(sorted((a,b)))
            if key in exposed:
                exposed.remove(key)
            else:
                exposed.add(key)
    foil={edge for edge,name in boundary.items() if name in ("main","flap")}
    if not foil<=exposed:
        raise RuntimeError("Cavity omitted part of the reference foil")
    exposed-=foil
    if any(edge in boundary for edge in exposed):
        raise RuntimeError("Cavity reaches reference domain boundary")
    neighbors={}
    for a,b in exposed:
        neighbors.setdefault(a,[]).append(b)
        neighbors.setdefault(b,[]).append(a)
    if any(len(v)!=2 for v in neighbors.values()):
        raise RuntimeError("Cavity boundary branches")
    first=min(neighbors)
    order=[first,neighbors[first][0]]
    while True:
        prev,last=order[-2:]
        new=next(n for n in neighbors[last] if n!=prev)
        if new==first:
            break
        order.append(new)
        if len(order)>len(neighbors):
            raise RuntimeError("Invalid cavity loop")
    if len(order)!=len(neighbors):
        raise RuntimeError("Cavity has multiple boundary loops")
    return kept,removed,np.array(order),{edge:name for edge,name in boundary.items() if edge not in foil}


def merge(xy, arrays, boundary, old_xy, kept, ring, outer_boundary):
    old_ids=sorted({node for cell in kept for node in cell})
    old_index={v:i for i,v in enumerate(old_ids)}
    joined=old_xy[old_ids].tolist()
    mapping={}
    interface={v for edge,name in boundary.items() if name=="interface" for v in edge}
    if len(interface)!=len(ring):
        raise RuntimeError("Cavity perimeter was subdivided")
    claimed=set()
    for i in sorted(interface):
        distance=np.linalg.norm(old_xy[ring]-xy[i],axis=1)
        j=int(ring[distance.argmin()])
        if distance.min()>1e-10 or j in claimed:
            raise RuntimeError("New interface does not match sealed coordinates one-to-one")
        claimed.add(j)
        mapping[i]=old_index[j]
    for i,point in enumerate(xy):
        if i not in mapping:
            mapping[i]=len(joined)
            joined.append(point.tolist())
    faces={tuple(sorted((old_index[a],old_index[b]))):name for (a,b),name in outer_boundary.items()}
    faces.update({tuple(sorted((mapping[a],mapping[b]))):name for (a,b),name in boundary.items() if name!="interface"})
    old_cells=[[old_index[v] for v in c] for c in kept]
    new_cells=[[mapping[int(v)] for v in c] for arr in arrays for c in arr]
    merged=old_cells+new_cells
    joined=np.array(joined)
    for original,mapped in zip(kept,old_cells):
        if not np.array_equal(old_xy[original],joined[mapped]):
            raise RuntimeError("Unchanged reference cell coordinates differ")
    return joined,merged,faces

def main():
    old_xy,old_cells,old_faces=reference_mesh()
    kept,removed,ring,outer_faces=cavity(old_xy,old_cells,old_faces)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("General.Verbosity", 2)
        gmsh.model.add("Sharp sealed NACA 66-012 MOD")
        geo = gmsh.model.geo
        groups = {}
        wall_curves = []
        prism_curves = []
        hinge_curves = []
        loops = []
        profile = solid("intact")
        points = []
        for a,b in zip(profile,np.roll(profile,-1,axis=0)):
            points.append(a)
            if (a[0]-hinge[0])*(b[0]-hinge[0])<0:
                t=(hinge[0]-a[0])/(b[0]-a[0])
                points.append(np.array([hinge[0],a[1]+t*(b[1]-a[1])]))
        poly=np.array(points)
        ids=[geo.addPoint(*p,0) for p in poly]
        lines=[geo.addLine(a,b) for a,b in zip(ids,ids[1:]+ids[:1])]
        groups["main"]=[]
        groups["flap"]=[]
        for a,b,line in zip(poly,np.roll(poly,-1,axis=0),lines):
            name="flap" if (a[0]+b[0])/2>hinge[0]+1e-10 else "main"
            groups[name].append(line)
            wall_curves.append(line)
            if name!="flap" or max(a[0],b[0])<1.188:
                prism_curves.append(line)
            if np.linalg.norm((a+b)/2-hinge)<.044:
                hinge_curves.append(line)
        loops.append(geo.addCurveLoop(lines))
        dom = [geo.addPoint(*old_xy[i],0) for i in ring]
        edges = [geo.addLine(a,b) for a,b in zip(dom,dom[1:]+dom[:1])]
        groups["interface"]=edges
        surf=geo.addPlaneSurface([geo.addCurveLoop(edges)]+loops)
        geo.synchronize()
        for edge in edges:
            gmsh.model.mesh.setTransfiniteCurve(edge,2)
        for name, curves in groups.items():
            gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, curves), name)
        gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [surf]), "water")
        f = gmsh.model.mesh.field

        def band(curves, near, inner, outer):
            dist = f.add("Distance")
            f.setNumbers(dist, "CurvesList", curves)
            f.setNumber(dist, "Sampling", 18)
            b = f.add("Threshold")
            for key, value in dict(InField=dist, SizeMin=near, SizeMax=.5, DistMin=inner, DistMax=outer).items():
                f.setNumber(b, key, value)
            return b

        bg = f.add("Min")
        f.setNumbers(bg, "FieldsList", [band(wall_curves, .009, .014, .85), band(hinge_curves, .00065, .0027, .017)])
        f.setAsBackgroundMesh(bg)
        bl = f.add("BoundaryLayer")
        f.setNumbers(bl, "CurvesList", prism_curves)
        for key, value in dict(Size=H1, Ratio=1.18, Thickness=THICKNESS, Quads=1).items():
            f.setNumber(bl, key, value)
        f.setAsBoundaryLayer(bl)
        for key, value in dict(MeshSizeFromPoints=0, MeshSizeFromCurvature=0, MeshSizeExtendFromBoundary=0, Algorithm=6).items():
            gmsh.option.setNumber("Mesh." + key, value)
        gmsh.model.mesh.generate(2)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xy = xyz.reshape(-1, 3)[:, :2]
        lookup = {int(tag): i for i, tag in enumerate(tags)}
        types, ids, conn = gmsh.model.mesh.getElements(2)
        cells = []
        arrays = []
        for typ, flat in zip(types, conn):
            n = {2: 3, 3: 4}[typ]
            arr = np.array([lookup[int(tag)] for tag in flat]).reshape(-1, n)
            polys = xy[arr]
            ccw = cross(polys, np.roll(polys, -1, axis=1)).sum(axis=1) > 0
            arr[~ccw] = arr[~ccw, ::-1]
            cells += arr.tolist()
            arrays.append(arr)
        boundary = {}
        for name, curves in groups.items():
            for c in curves:
                for connectivity in gmsh.model.mesh.getElements(1, c)[2]:
                    for a, b in connectivity.reshape(-1, 2):
                        boundary[tuple(sorted((lookup[int(a)], lookup[int(b)])))] = name
        gmsh.write(str(OUT / "cavity_gmsh.msh"))
    finally:
        gmsh.finalize()

    xy,cells,boundary=merge(xy,arrays,boundary,old_xy,kept,ring,outer_faces)
    arrays=[np.array([c for c in cells if len(c)==n]) for n in (3,4)]
    wall_nodes = {name: np.unique([edge for edge, lab in boundary.items() if lab == name]) for name in ("main", "flap")}
    weight = weights(xy)
    assert np.max(abs(weight[wall_nodes["main"]])) < 1e-8, np.max(weight[wall_nodes["main"]])
    flap_aft = wall_nodes["flap"][xy[wall_nodes["flap"],0] >= hinge[0]+.035]
    assert len(flap_aft)>0 and np.max(abs(weight[flap_aft] - 1)) < 1e-8
    worst_area = float("inf")
    worst_corner = float("inf")
    worst_angle = None
    for delta in np.linspace(-2, 2, 41):
        nodes = move(xy, delta)
        for arr in arrays:
            p = nodes[arr]
            side = np.roll(p, -1, axis=1) - p
            area = .5*cross(p, np.roll(p, -1, axis=1)).sum(axis=1)
            corner = cross(side, np.roll(side, -1, axis=1))
            if delta in (-2, 0, 2) and np.any(corner.min(axis=1) <= 0):
                bad = p[corner.min(axis=1) <= 0].mean(axis=1)
                print("Bad corners",delta, len(bad), bad[:30])
            worst_area = min(worst_area, float(area.min()))
            if corner.min() < worst_corner:
                worst_corner, worst_angle = float(corner.min()), float(delta)
    quad_count = sum(len(arr) for arr in arrays if arr.shape[1] == 4)
    adjacency = {}
    for cid, cell in enumerate(cells):
        for a,b in zip(cell,cell[1:]+cell[:1]):
            adjacency.setdefault(tuple(sorted((a,b))),[]).append(cid)
    wall_quads = {name: sum(len(cells[adjacency[edge][0]]) == 4 for edge, lab in boundary.items() if lab == name)
                  for name in wall_nodes}
    wall_faces = {name: sum(lab == name for lab in boundary.values()) for name in wall_nodes}
    np.savez_compressed(OUT / "plot_mesh.npz", xy=xy,
                        triangles=np.concatenate([arr for arr in arrays if arr.shape[1] == 3]),
                        quads=np.concatenate([arr for arr in arrays if arr.shape[1] == 4]),
                        main=np.array([edge for edge, lab in boundary.items() if lab == "main"]),
                        flap=np.array([edge for edge, lab in boundary.items() if lab == "flap"]))
    audit = dict(cells=len(cells), sealed_outer_source=str(SEALED),
                 sealed_outer_sha256=hashlib.sha256(SEALED.read_bytes()).hexdigest(),
                 sealed_cells_unchanged=len(kept), sealed_cells_replaced=len(removed),
                 patch_interface_vertices=len(ring), sealed_external_boundary_faces=len(outer_faces),
                 domain_bounds_m=[xy.min(axis=0).tolist(),xy.max(axis=0).tolist()], quadrilaterals=quad_count, wall_quads=wall_quads, wall_faces=wall_faces,
                 trailing_edge_layer_cutoff_m=1.188, source=str(SOURCE), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 first_layer_design_m=H1, layer_growth=1.18, nominal_layer_count=3, gap_nominal_m=0., sharp_trailing_edge=True, trailing_edge_x_m=float(xy[wall_nodes["flap"],0].max()),
                 polygon_simplification_tolerance_m=PROFILE_TOL, minimum_area_m2=worst_area,
                 minimum_corner_cross_m2=worst_corner, worst_corner_angle_deg=worst_angle,
                 maximum_main_weight=float(np.max(weight[wall_nodes["main"]])),
                 minimum_rigid_flap_weight=float(np.min(weight[flap_aft])), sealed_blend_length_m=.035)
    print(json.dumps(audit, indent=2), flush=True)
    if worst_area <= 0 or worst_corner <= 0 or quad_count == 0:
        raise RuntimeError("Mesh failed the offline motion or layer check")
    write_fluent(xy, cells, boundary)
    audit["mesh_sha256"] = hashlib.sha256((OUT / "mesh_2d.msh").read_bytes()).hexdigest()
    (OUT / "MESH_AUDIT.json").write_text(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()


