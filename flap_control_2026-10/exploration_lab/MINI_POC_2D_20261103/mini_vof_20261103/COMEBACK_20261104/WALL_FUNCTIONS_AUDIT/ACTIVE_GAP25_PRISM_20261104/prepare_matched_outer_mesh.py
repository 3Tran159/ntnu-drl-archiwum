from pathlib import Path

root=Path(__file__).resolve().parent
out=root/"SEALED_OUTER_MESH_GAPPED"
out.mkdir(exist_ok=False)
src=root/"TRAILING_EDGE_LAYER_RELIEF"/"build_gap_mesh.py"
s=src.read_text(encoding="utf8")

insert=r'''
SEALED = OUT.parents[2]/"COARSE_FACETED_OPEN_CELLS"/"geometry_and_mesh.msh"


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
'''
s=s.replace('def main():\n    gmsh.initialize()',insert+'''
def main():
    old_xy,old_cells,old_faces=reference_mesh()
    kept,removed,ring,outer_faces=cavity(old_xy,old_cells,old_faces)
    gmsh.initialize()''',1)
start=s.index('        dom = [geo.addPoint')
end=s.index('        for name, curves in groups.items():',start)
s=s[:start]+'''        dom = [geo.addPoint(*old_xy[i],0) for i in ring]
        edges = [geo.addLine(a,b) for a,b in zip(dom,dom[1:]+dom[:1])]
        groups["interface"]=edges
        surf=geo.addPlaneSurface([geo.addCurveLoop(edges)]+loops)
        geo.synchronize()
        for edge in edges:
            gmsh.model.mesh.setTransfiniteCurve(edge,2)
'''+s[end:]
s=s.replace('    wall_nodes =','''    xy,cells,boundary=merge(xy,arrays,boundary,old_xy,kept,ring,outer_faces)
    arrays=[np.array([c for c in cells if len(c)==n]) for n in (3,4)]
    wall_nodes =''',1)
s=s.replace('("interior", "main", "flap", "inlet", "outlet", "farfield")','("interior", "main", "flap", "inlet", "outlet", "top", "bottom")')
s=s.replace('"farfield": (7, "symmetry")','"top": (7, "symmetry"), "bottom": (7, "symmetry")')
s=s.replace('audit = dict(cells=len(cells),','audit = dict(cells=len(cells), sealed_outer_source=str(SEALED),\n                 sealed_outer_sha256=hashlib.sha256(SEALED.read_bytes()).hexdigest(),\n                 sealed_cells_unchanged=len(kept), sealed_cells_replaced=len(removed),\n                 patch_interface_vertices=len(ring), sealed_external_boundary_faces=len(outer_faces),\n                 domain_bounds_m=[xy.min(axis=0).tolist(),xy.max(axis=0).tolist()],')
(out/"build_matched_mesh.py").write_text(s,encoding="utf8")

