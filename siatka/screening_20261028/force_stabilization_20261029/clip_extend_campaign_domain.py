"""Conservative remote x clipping/extension of an exact one-span CGNS mesh.
File processing only: never starts STAR, touches solver locks, or changes a source.
"""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import sys, json, csv, math, shutil, hashlib, collections, argparse
from pathlib import Path
sys.path.insert(0, "F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311")
import numpy as np
import h5py

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8*1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def area(points, poly):
    p = np.asarray([points[int(v)] for v in poly], dtype=float)[:, [0,2]]
    q = p - p[0]
    return float(.5*np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1)))

def decode_polys(g):
    off = g["ElementStartOffset/ data"][...]
    conn = g["ElementConnectivity/ data"][...] - 1
    return [conn[off[i]:off[i+1]].copy() for i in range(len(off)-1)]

def clip_halfplane(poly, points, plane, keep_greater, registry):
    """Shared edge/plane intersections have one canonical node ID."""
    def inside(i):
        return points[i][0] >= plane if keep_greater else points[i][0] <= plane
    def intersection(a, b):
        if points[a][0] == plane: return a
        if points[b][0] == plane: return b
        aa, bb = sorted((int(a), int(b)))
        key = (aa, bb, float(plane))
        if key not in registry:
            p, q = points[aa], points[bb]
            t = (plane-p[0])/(q[0]-p[0])
            if not -1e-14 <= t <= 1+1e-14:
                raise RuntimeError("Intersection lies outside original edge")
            registry[key] = len(points)
            points.append([float(plane), float(p[1]), float(p[2]+t*(q[2]-p[2]))])
        return registry[key]
    out = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        ia, ib = inside(a), inside(b)
        if ia and ib: out.append(b)
        elif ia and not ib: out.append(intersection(a,b))
        elif not ia and ib: out.extend((intersection(a,b),b))
    clean=[]
    for i in out:
        if not clean or clean[-1] != i: clean.append(i)
    if len(clean)>1 and clean[0]==clean[-1]: clean.pop()
    return clean

def owners_of(surface):
    edges=collections.defaultdict(list)
    for ci,p in enumerate(surface):
        for a,b in zip(p,p[1:]+p[:1]):
            edges[tuple(sorted((a,b)))].append((ci,a,b))
    return edges

def assert_simple(points, poly):
    p=np.array([points[v] for v in poly])[:,[0,2]]
    if len(set(poly))!=len(poly): raise RuntimeError("Repeated polygon node")
    def cross(a,b): return a[0]*b[1]-a[1]*b[0]
    for i in range(len(p)):
        a,b=p[i],p[(i+1)%len(p)]
        for j in range(i+2,len(p)):
            if i==0 and j==len(p)-1: continue
            c,d=p[j],p[(j+1)%len(p)]
            if cross(b-a,c-a)*cross(b-a,d-a)<0 and cross(d-c,a-c)*cross(d-c,b-c)<0:
                raise RuntimeError("Clipped polygon self-intersection")

def build(source, target_dir, xmin, xmax, dxmax=.2, protected_x=(-5.,5.)):
    source=Path(source).resolve(); out=Path(target_dir).resolve()
    if not source.is_file(): raise RuntimeError("Source CGNS missing")
    if out.exists(): raise RuntimeError("Existing attempt preserved: "+str(out))
    if not xmin<protected_x[0]<protected_x[1]<xmax:
        raise RuntimeError("Requested bounds intersect protected near-foil interval")
    if dxmax<=0: raise RuntimeError("Invalid maximum remote spacing")
    out.mkdir(parents=False)
    source_sha=sha(source)
    identity={"source":str(source),"source_sha256":source_sha,"target":str(out),
              "requested_x_bounds_m":[xmin,xmax],"flow_steps":0,"workers":1,"gpu":False}
    (out/"source_identity.json").write_text(json.dumps(identity,indent=2))
    with h5py.File(source,"r") as f:
        z=f["Base/fluid"]
        xyz0=np.column_stack([z["GridCoordinates/Coordinate"+a+"/ data"][...] for a in "XYZ"])
        source_polys=decode_polys(z["Q2D_span_source"])
        used=np.unique(np.concatenate(source_polys))
        if np.max(np.abs(xyz0[used,1]-.01))>1e-12:
            raise RuntimeError("Source plane not y=.01")
        remap=np.full(len(xyz0),-1,dtype=np.int64); remap[used]=np.arange(len(used))
        points=xyz0[used].tolist()
        original=[list(map(int,remap[p])) for p in source_polys]
        original_areas=[]
        for i,p in enumerate(original):
            a=area(points,p)
            if abs(a)<1e-18: raise RuntimeError("Zero-area source polygon")
            if a<0: original[i]=p[::-1];a=-a
            original_areas.append(a)
        groups=[n for n,g in z.items() if isinstance(g,h5py.Group)
                and g.attrs.get("label")==b"Elements_t" and int(g[" data"][0])==22]
        boundary_map={}
        for name in groups:
            if name in ("Polyfaces_fluid","Q2D_span_source","Q2D_span_target"): continue
            for p in decode_polys(z[name]):
                for a,b in zip(p,np.roll(p,-1)):
                    if remap[a]>=0 and remap[b]>=0:
                        edge=tuple(sorted((int(remap[a]),int(remap[b]))))
                        if edge in boundary_map and boundary_map[edge]!=name:
                            raise RuntimeError("Source boundary identities disagree")
                        boundary_map[edge]=name
    def bname(suffix):
        found=[x for x in groups if x.endswith("."+suffix)]
        if len(found)!=1: raise RuntimeError("Ambiguous boundary "+suffix)
        return found[0]
    foil_names=[x for x in groups if x=="HF_012_wall"]
    if len(foil_names)!=1: raise RuntimeError("Foil boundary missing")
    x0=min(p[0] for p in points);x1=max(p[0] for p in points)
    z0=min(p[2] for p in points);z1=max(p[2] for p in points)
    if abs(z0+22)>1e-10 or abs(z1-8)>1e-10:
        raise RuntimeError("Vertical domain differs from retained H24 scope")
    if not x0<protected_x[0]<protected_x[1]<x1:
        raise RuntimeError("Unexpected source protected interval")
    source_node_count=len(points)
    clipmin=max(xmin,x0);clipmax=min(xmax,x1)
    registry={}; surface=[];mapping=[]; cropped=[];out_source=[]
    for i,p in enumerate(original):
        xs=[points[v][0] for v in p]
        if min(xs)>=clipmin and max(xs)<=clipmax:
            q=p[:];status="keep"
        elif max(xs)<=clipmin or min(xs)>=clipmax:
            q=[];status="remove"
        else:
            q=clip_halfplane(p,points,clipmin,True,registry)
            q=clip_halfplane(q,points,clipmax,False,registry) if q else []
            status="crop" if len(q)>=3 else "remove"
        if len(q)>=3:
            a=area(points,q)
            if a<=1e-18: raise RuntimeError("Nonpositive clipped polygon")
            if status=="crop": assert_simple(points,q);cropped.append(i)
            oi=len(surface);surface.append(q);out_source.append(i)
        else: oi=-1;a=0.
        if max(xs)>=protected_x[0] and min(xs)<=protected_x[1] and status!="keep":
            raise RuntimeError("Protected source cell was modified")
        mapping.append([i,oi,status,len(p),len(q),original_areas[i],a])
    edges=owners_of(surface)
    labels={}
    for edge,owners in edges.items():
        if len(owners)==2:
            if owners[0][1:]!=owners[1][1:][::-1]:
                raise RuntimeError("Same-direction shared edge")
        elif len(owners)==1:
            xx=[points[v][0] for v in edge];zz=[points[v][2] for v in edge]
            if max(abs(v-clipmin) for v in xx)<1e-10: name=bname("inlet")
            elif max(abs(v-clipmax) for v in xx)<1e-10: name=bname("outlet")
            elif max(abs(v-z0) for v in zz)<1e-10: name=bname("bottom")
            elif max(abs(v-z1) for v in zz)<1e-10: name=bname("top")
            else: name=boundary_map.get(edge)
            if name is None: raise RuntimeError("Unlabelled exposed edge")
            labels[edge]=name
        else: raise RuntimeError("Nonmanifold edge after clipping")
    extensions=[]
    for side,old,new in (("inlet",clipmin,xmin),("outlet",clipmax,xmax)):
        if old==new: continue
        name=bname(side); wall=[e for e,n in labels.items() if n==name]
        ids=sorted({v for e in wall for v in e},key=lambda v:points[v][2])
        if len(ids)!=len(wall)+1 or {tuple(sorted(e)) for e in zip(ids[:-1],ids[1:])}!=set(wall):
            raise RuntimeError("Remote boundary not one conforming vertical chain")
        cols=math.ceil(abs(new-old)/dxmax); prev=ids
        for xx in np.linspace(old,new,cols+1)[1:]:
            cur=[]
            for v in ids:
                cur.append(len(points));points.append([float(xx),.01,float(points[v][2])])
            for j in range(len(ids)-1):
                a,b=prev[j:j+2];c,d=cur[j:j+2]
                p=[c,a,b,d] if new<old else [a,c,d,b]
                if area(points,p)<=0: raise RuntimeError("Bad extension area")
                surface.append(p);out_source.append(-1)
            labels[tuple(sorted((prev[0],cur[0])))]=bname("bottom")
            labels[tuple(sorted((prev[-1],cur[-1])))]=bname("top")
            prev=cur
        for a,b in zip(prev[:-1],prev[1:]):labels[tuple(sorted((a,b)))]=name
        extensions.append({"side":side,"old_x_m":old,"new_x_m":new,"columns":cols,
                           "rows":len(ids)-1,"dx_m":abs(new-old)/cols})
    # Compact unused source/cropped-away nodes without changing any retained coordinates.
    active=sorted({v for p in surface for v in p})
    reindex={v:i for i,v in enumerate(active)}
    compact=[points[v] for v in active]
    surface=[[reindex[v] for v in p] for p in surface]
    labels={tuple(sorted((reindex[a],reindex[b]))):name for (a,b),name in labels.items()
            if a in reindex and b in reindex}
    N=len(compact);C=len(surface)
    xyz=np.vstack((np.asarray(compact),np.asarray(compact)));xyz[:N,1]=.01;xyz[N:,1]=.03
    edges=owners_of(surface); face_groups={name:[] for name in groups};face_edges={}
    for edge,owners in edges.items():
        if len(owners)==2:
            if owners[0][1:]!=owners[1][1:][::-1]:raise RuntimeError("Shared edge orientation")
            name="Polyfaces_fluid"
        elif len(owners)==1:
            if edge not in labels:raise RuntimeError("Missing final boundary label")
            name=labels[edge]
        else: raise RuntimeError("Final nonmanifold edge")
        _,a,b=owners[0]
        face_edges[edge]=(name,len(face_groups[name]))
        face_groups[name].append(np.array([a,a+N,b+N,b],dtype=np.int64)+1)
    face_groups["Q2D_span_source"]=[np.array(p,dtype=np.int64)+1 for p in surface]
    face_groups["Q2D_span_target"]=[np.array(p[::-1],dtype=np.int64)+N+1 for p in surface]
    ranges={};start=1
    for name in groups:
        count=len(face_groups[name])
        if count==0: raise RuntimeError("Empty expected face section: "+name)
        ranges[name]=(start,start+count-1);start+=count
    cellfaces=[]
    for ci,p in enumerate(surface):
        faces=[ranges["Q2D_span_source"][0]+ci,ranges["Q2D_span_target"][0]+ci]
        for a,b in zip(p,p[1:]+p[:1]):
            e=tuple(sorted((a,b)));name,j=face_edges[e];fid=ranges[name][0]+j
            faces.append(fid if edges[e][0][0]==ci else -fid)
        cellfaces.append(np.asarray(faces,dtype=np.int64))
    target=out/"mesh.CGNS";shutil.copy2(source,target)
    with h5py.File(target,"r+") as f:
        z=f["Base/fluid"]
        def data(g,v):
            if " data" in g:del g[" data"]
            g.create_dataset(" data",data=v)
        data(z,np.array([[2*N],[C],[0]],dtype=np.int64))
        for i,a in enumerate("XYZ"):data(z["GridCoordinates/Coordinate"+a],xyz[:,i])
        for name in groups+["fluid"]:
            pp=face_groups[name] if name!="fluid" else cellfaces
            rr=ranges[name] if name!="fluid" else (start,start+C-1)
            data(z[name+"/ElementRange"],np.array(rr,dtype=np.int64))
            data(z[name+"/ElementStartOffset"],np.r_[0,np.cumsum([len(v) for v in pp])].astype(np.int64))
            data(z[name+"/ElementConnectivity"],np.concatenate(pp).astype(np.int64))
            if name in z["ZoneBC"]:
                data(z["ZoneBC/"+name+"/PointRange"],np.array(rr,dtype=np.int64).reshape(2,1))
        for name in list(z):
            if isinstance(z[name],h5py.Group) and z[name].attrs.get("label") in (b"FlowSolution_t",b"ZoneIterativeData_t"):del z[name]
        for name in list(f["Base"]):
            if isinstance(f["Base"][name],h5py.Group) and f["Base"][name].attrs.get("label")==b"BaseIterativeData_t":del f["Base"][name]
    with (out/"source_cell_map.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["source_cell_index0","output_cell_index0","status","source_vertices","output_vertices","source_area_m2","retained_area_m2"]);w.writerows(mapping)
    with (out/"output_cell_map.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["output_cell_index0","source_cell_index0","status"])
        for i,src in enumerate(out_source):w.writerow([i,src,"extension" if src<0 else mapping[src][2]])
    with (out/"source_node_map.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["source_global_node_index0","output_span_source_index0"])
        for old in active:
            if old<source_node_count:w.writerow([int(used[old]),reindex[old]])
    intersections=[{"edge_source_plane_node_ids0":[a,b],"x_plane_m":x,"generated_node_id0":v,
                    "output_node_id0":reindex.get(v),"position":points[v]} for (a,b,x),v in registry.items()]
    (out/"canonical_intersections.json").write_text(json.dumps(intersections,indent=2))
    expected_area=(xmax-xmin)*(z1-z0)-( (x1-x0)*(z1-z0)-math.fsum(original_areas))
    output_area=math.fsum(area(compact,p) for p in surface)
    if abs(output_area-expected_area)>1e-7:raise RuntimeError("Conservative area mismatch")
    if sha(source)!=source_sha:raise RuntimeError("Source hash changed")
    counts=dict(collections.Counter(r[2] for r in mapping))
    result={**identity,"status":"file_geometry_built_pending_independent_audit",
            "source_unchanged":True,"source_cells":len(original),"cells":C,"source_cell_status_counts":counts,
            "extension_cells":sum(x<0 for x in out_source),"extensions":extensions,
            "source_bounds_m":[x0,x1,z0,z1],"target_bounds_m":[xmin,xmax,z0,z1],"span_m":.02,
            "protected_x_interval_m":list(protected_x),"protected_cells_preserved":True,
            "canonical_intersection_count":len(registry),"expected_area_m2":expected_area,
            "actual_area_m2":output_area,"expected_volume_m3":expected_area*.02,
            "actual_volume_m3":output_area*.02,"output_sha256":sha(target),
            "pending":["Independent signed-NFACE topology and source-preservation audit",
                       "STAR import and native cell-quality audit","Matched calm and all wave numerical/propagation accuracy checks"]}
    (out/"build_result.json").write_text(json.dumps(result,indent=2))
    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("source");ap.add_argument("target_dir");ap.add_argument("xmin",type=float);ap.add_argument("xmax",type=float);ap.add_argument("--dxmax",type=float,default=.2)
    a=ap.parse_args();print(json.dumps(build(a.source,a.target_dir,a.xmin,a.xmax,a.dxmax)),flush=True)
