import json
from pathlib import Path
import sys

import numpy as np

D = Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_day import sha

SOURCE = D.parent/"WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104"
NAMES = {"sealed":"SEALED_SHARP_MATCHED_OUTER","gap":"SEALED_OUTER_MESH_GAPPED"}
WIDTH = .02
HX, HY = .952, .02128173276777


def smooth(s):
    q=np.clip(s,0,1)
    return q**3*(10-15*q+6*q*q)


def geometry(source, is_gap):
    meta=json.loads((source/"MESH_AUDIT.json").read_text())
    if sha(source/"mesh_2d.msh") != meta["mesh_sha256"]:
        raise RuntimeError("Matched source mesh hash mismatch")
    m=np.load(source/"plot_mesh.npz")
    xy=m["xy"]
    arrays=[m["triangles"],m["quads"]]
    if sum(map(len,arrays))!=meta["cells"]:
        raise RuntimeError("Matched source topology count mismatch")
    minima=[]
    x,y=(xy-[HX,HY]).T
    r=np.hypot(x,y)
    blend=np.maximum(smooth((.03755-r)/.00235),smooth((x+.00745)/.00745)) if is_gap else smooth(x/.035)
    weight=blend*smooth((1.4-r)/1.1)
    for angle in np.linspace(-5,5,101):
        a=np.deg2rad(angle)*weight
        pts=np.column_stack((HX+x*np.cos(a)+y*np.sin(a),HY-x*np.sin(a)+y*np.cos(a)))
        for group in arrays:
            verts=pts[group]
            e=np.roll(verts,-1,axis=1)-verts
            f=np.roll(e,-1,axis=1)
            cross=e[:,:,0]*f[:,:,1]-e[:,:,1]*f[:,:,0]
            minima.append((float(cross.min()),float(angle)))
    return m,arrays,meta,min(minima)


def extrude(key, mesh, arrays, meta, worst):
    out=D/"VOF_MESH"/key
    out.mkdir(parents=True,exist_ok=False)
    xy=mesh["xy"]
    base=np.column_stack((xy,np.zeros(len(xy))))
    nodes=np.vstack((base,base+[0,0,WIDTH]))
    cells=[list(map(int,cell)) for a in arrays for cell in a]
    edges={tuple(sorted(map(int,edge))):name for name in ("main","flap") for edge in mesh[name]}
    faces={}
    nn=len(base)
    for cid,cell in enumerate(cells,1):
        rings=[list(reversed(cell)),[v+nn for v in cell]]
        rings += [[u,v,v+nn,u+nn] for u,v in zip(cell,cell[1:]+cell[:1])]
        for face in rings:
            key_face=tuple(sorted(face))
            if key_face in faces:
                if faces[key_face][-1]!=0:
                    raise RuntimeError("Nonmanifold extruded face")
                faces[key_face][-1]=cid
            else:
                faces[key_face]=face+[cid,0]
    zones={name:[] for name in ("interior","main","flap","inlet","outlet","top","bottom","span_front","span_back")}
    outer=0
    for key_face,face in faces.items():
        if face[-1]: name="interior"
        elif all(v<nn for v in key_face): name="span_front"
        elif all(v>=nn for v in key_face): name="span_back"
        else:
            edge=tuple(v for v in key_face if v<nn)
            name=edges.get(edge)
            if name is None:
                outer+=1
                points=xy[list(edge)]
                name=next((n for n,axis,pos in (("inlet",0,-12),("outlet",0,28),("top",1,4),("bottom",1,-10))
                           if np.all(np.abs(points[:,axis]-pos)<1e-9)),None)
                if name is None:
                    raise RuntimeError("Unclassified extruded side face")
        zones[name].append(face)
    if outer!=meta["sealed_external_boundary_faces"] or any(not v for v in zones.values()):
        raise RuntimeError("Boundary count mismatch")
    h=lambda n: format(n,"x")
    file=out/"mesh_3d.msh"
    with file.open("x") as f:
        f.write(f'(0 "Matched hydrofoil quasi-2D")\n(2 3)\n(10 (0 1 {h(len(nodes))} 0 3))\n(10 (1 1 {h(len(nodes))} 1 3)(\n')
        f.writelines(f"{x:.15g} {y:.15g} {z:.15g}\n" for x,y,z in nodes)
        f.write(f'))\n(12 (0 1 {h(len(cells))} 0))\n(12 (1 1 {h(len(cells))} 1 0)(\n')
        f.write(" ".join("6" if len(cell)==3 else "4" for cell in cells))
        f.write(f"\n))\n(13 (0 1 {h(len(faces))} 0))\n")
        first=1
        for zid,(name,group) in enumerate(zones.items(),2):
            bc=2 if name=="interior" else 3 if name in ("main","flap","bottom") else 10 if name=="inlet" else 7 if name.startswith("span") else 5
            sizes={len(face)-2 for face in group}
            ft=next(iter(sizes)) if len(sizes)==1 else 0
            last=first+len(group)-1
            f.write(f"(13 ({h(zid)} {h(first)} {h(last)} {h(bc)} {h(ft)})(\n")
            for face in group:
                vertices=face[:-2][::-1]
                f.write(("" if ft else h(len(vertices))+" ")+" ".join([h(v+1) for v in vertices]+[h(v) for v in face[-2:]])+"\n")
            label={2:"interior",3:"wall",10:"velocity-inlet",5:"pressure-outlet",7:"symmetry"}[bc]
            f.write(f"))\n(45 ({zid} {label} {name})())\n")
            first=last+1
        f.write("(45 (1 fluid MINI_water_air)())\n")
    result={"cells":len(cells),"span_m":WIDTH,"sha256":sha(file),"path":str(file),
            "minimum_original_volume_m3":meta["minimum_area_m2"]*WIDTH,
            "boundary_face_counts":{name:len(group) for name,group in zones.items()},
            "min_signed_corner_cross_plus_minus_5":worst[0],"worst_angle_deg":worst[1],
            "native_import":"PENDING"}
    (out/"AUDIT.json").write_text(json.dumps(result,indent=2))
    print(key, json.dumps(result), flush=True)
    return result


if __name__=="__main__":
    pair={}
    for key, name in NAMES.items():
        m, cells, meta, worst=geometry(SOURCE/name,key=="gap")
        pair[key]=extrude(key,m,cells,meta,worst)
    (D/"VOF_MESH"/"PAIR.json").write_text(json.dumps(pair,indent=2))

