import json,math,csv,hashlib
from pathlib import Path
root=Path(r"F:\ntnu\mesh_screening_20261028\block1_20261029")
def sub(a,b): return [a[i]-b[i] for i in range(3)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): return math.sqrt(sum(v*v for v in a))
def stl_metrics(path):
    pts=[]
    for line in path.read_text().splitlines():
        x=line.split()
        if x and x[0]=='vertex':pts.append(tuple(map(float,x[1:4])))
    if len(pts)%3: raise ValueError("Invalid STL vertex count")
    triangles=[pts[i:i+3] for i in range(0,len(pts),3)]
    bounds=[[min(p[k] for p in pts),max(p[k] for p in pts)] for k in range(3)]
    area=volume=0.;projected=[0.,0.,0.]
    for a,b,c in triangles:
        cr=cross(sub(b,a),sub(c,a));area+=norm(cr)/2
        for k in range(3):projected[k]+=abs(cr[k])/4
        cc=cross(b,c);volume+=sum(a[k]*cc[k] for k in range(3))/6
    sections=[]
    for y in [0.,1.,2.75,4.,5.,5.499]:
        pp=[]
        for tri in triangles:
            for a,b in zip(tri,tri[1:]+tri[:1]):
                if abs(a[1]-b[1])<1e-12:continue
                t=(y-a[1])/(b[1]-a[1])
                if -1e-10<=t<=1+1e-10:pp.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(3)))
        if pp:
            le=min(pp,key=lambda p:p[0]);te=max(pp,key=lambda p:p[0])
            sections.append({"y":y,"xmin_point":le,"xmax_point":te,"x_extent":te[0]-le[0],"zmin":min(p[2] for p in pp),"zmax":max(p[2] for p in pp),"extremal_chord_incidence_deg":math.degrees(math.atan2(le[2]-te[2],te[0]-le[0]))})
    return {"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"triangles":len(triangles),"bounds":bounds,"surface_area":area,"enclosed_volume_abs":abs(volume),"half_sum_absolute_projected_area_yz_xz_xy":projected,"sections":sections}
result={"stl":[stl_metrics(root/"foil_original.stl"),stl_metrics(root/"foil_fine.stl")]}
with open(r"E:\ntnu_cfd_night_20261028\D002\foil_final_fields.csv",newline='') as f:
    reader=csv.reader(f);headers=next(reader)
    print("CSV_HEADERS",headers)
    ix=[i for i,h in enumerate(headers) if h.strip().strip('"') in ("X (m)","Y (m)","Z (m)")]
    if len(ix)==3:
        lows=[float('inf')]*3;highs=[-float('inf')]*3;n=0
        for row in reader:
            if not row:continue
            n+=1
            for k,i in enumerate(ix):
                v=float(row[i]);lows[k]=min(lows[k],v);highs[k]=max(highs[k],v)
        result["D002_wall_centroid_bounds"]={"n":n,"headers":[headers[i] for i in ix],"min":lows,"max":highs}
(root/"geometry_metrics.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
