from collections import Counter
from pathlib import Path
import json
import sys
import numpy as np

d = Path(__file__).resolve().parent
reference = d.parent / "WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104/SEALED_SHARP_MATCHED_OUTER/plot_mesh.npz"
data = np.load(reference)
xy = data["xy"]
cells = [tuple(map(int, c)) for key in ("triangles", "quads") for c in data[key]]
wall = {tuple(sorted(map(int, edge))): name for name in ("Main", "Flap") for edge in data[name.lower()]}
z = 0.02
patches = {name: [] for name in ("Span0", "Span1", "Main", "Flap", "Inlet", "Outlet", "Bottom", "Top")}
def xyz(i, layer):
    return (*map(float, xy[i]), layer*z)
edges = Counter()
directed = {}
for cell in cells:
    v = xy[list(cell)]
    area2 = sum(a[0]*b[1] - b[0]*a[1] for a,b in zip(v,np.roll(v,-1,axis=0)))
    assert area2 != 0
    if area2 < 0:
        cell = cell[::-1]
    for u,v in zip(cell, cell[1:]+cell[:1]):
        key = tuple(sorted((u,v)))
        edges[key] += 1
        directed[key] = (u,v)
    for i in range(1,len(cell)-1):
        tri=(cell[0],cell[i],cell[i+1])
        patches["Span0"].append(tuple(xyz(k,0) for k in reversed(tri)))
        patches["Span1"].append(tuple(xyz(k,1) for k in tri))
for edge,n in edges.items():
    assert n in (1,2)
    if n != 1:
        continue
    u,v=directed[edge]
    name=wall.get(edge)
    if name is None:
        a,b=xy[[u,v]]
        matches=[label for idx,val,label in [(0,-12,"Inlet"),(0,28,"Outlet"),(1,-10,"Bottom"),(1,4,"Top")] if abs(a[idx]-val)<1e-8 and abs(b[idx]-val)<1e-8]
        assert len(matches)==1,(a,b)
        name=matches[0]
    a,b,c,e=xyz(u,0),xyz(v,0),xyz(v,1),xyz(u,1)
    patches[name].extend([(a,b,c),(a,c,e)])
assert all(edges[k]==1 for k in wall)
stl_edges=Counter()
with (d/"SharpSealedFluidDomain.stl").open("w",newline="\n") as out:
    for name,faces in patches.items():
        assert faces
        out.write(f"solid {name}\n")
        for a,b,c in faces:
            ax,ay,az=(q-p for p,q in zip(a,b))
            bx,by,bz=(q-p for p,q in zip(a,c))
            n=(ay*bz-az*by,az*bx-ax*bz,ax*by-ay*bx)
            length=sum(x*x for x in n)**0.5
            assert length>0
            out.write("  facet normal " + " ".join(f"{v/length:.9g}" for v in n) + "\n    outer loop\n")
            for vertex in (a,b,c):
                out.write("      vertex "+" ".join(f"{v:.17g}" for v in vertex)+"\n")
            out.write("    endloop\n  endfacet\n")
            stl_edges.update(tuple(sorted(k)) for k in [(a,b),(b,c),(c,a)])
        out.write(f"endsolid {name}\n")
assert set(stl_edges.values())=={2}, Counter(stl_edges.values())
(d/"GEOMETRY_AUDIT.json").write_text(json.dumps({"source":str(reference),"reference_cells":len(cells),"span_m":z,"extent_xy_m":[xy.min(axis=0).tolist(),xy.max(axis=0).tolist()],"foil_wall_edges":len(wall),"patch_triangles":{k:len(v) for k,v in patches.items()},"watertight":True},indent=2))

