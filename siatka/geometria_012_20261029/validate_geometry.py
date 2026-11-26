import json,math,struct,collections,hashlib
from pathlib import Path
r=Path(r"F:\ntnu\geometry_012_20261029")
m=json.loads((r/"profile_point_replacement.json").read_text())
def read_stl(path,scale):
    data=path.read_bytes()
    if len(data)>=84 and len(data)==84+50*struct.unpack_from("<I",data,80)[0]:
        tris=[]
        for i in range(struct.unpack_from("<I",data,80)[0]):
            v=struct.unpack_from("<12fH",data,84+50*i)
            tris.append([tuple(scale*x for x in v[j:j+3]) for j in [3,6,9]])
        return tris
    p=[tuple(scale*float(x) for x in l.split()[1:4]) for l in data.decode().splitlines() if l.split() and l.split()[0]=="vertex"]
    return [p[i:i+3] for i in range(0,len(p),3)]
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def measure(tris,name,refs):
    points=[p for t in tris for p in t];edges=collections.Counter();vol=areaXY=area=0.
    for t in tris:
        a,b,c=t
        n=cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))
        area+=math.sqrt(sum(v*v for v in n))/2
        areaXY+=abs(n[2])/4
        vol+=sum(a[i]*cross(b,c)[i] for i in range(3))/6
        for a,b in zip(t,t[1:]+t[:1]):
            edges[tuple(sorted((tuple(round(v,8) for v in a),tuple(round(v,8) for v in b))))]+=1
    stations=[]
    plot=None
    for y in [-5.4,-4.125,-1.375,0,1.375,4.125,5.4]:
        c=1.19 if abs(y)<=2.75 else 1.19*(1+(.33-1)*(abs(y)-2.75)/2.75)
        xle=.25*(1.19-c)
        segs=[]
        for t in tris:
            hits=[]
            for a,b in zip(t,t[1:]+t[:1]):
                if abs(b[1]-a[1])<1e-12:continue
                u=(y-a[1])/(b[1]-a[1])
                if -1e-10<=u<=1+1e-10:
                    p=(a[0]+u*(b[0]-a[0]),a[2]+u*(b[2]-a[2]))
                    if not any(math.dist(p,q)<1e-9 for q in hits):hits.append(p)
            if len(hits)==2:segs.append(hits)
        def at(x):
            zs=[]
            for (a,z),(b,w) in segs:
                if abs(b-a)<1e-12:continue
                u=(x-a)/(b-a)
                if -1e-9<=u<=1+1e-9:zs.append(z+u*(w-z))
            return (min(zs),max(zs)) if zs else None
        samples=[]
        for i in range(1,2000):
            x=i/2000;pair=at(xle+c*x)
            if pair:samples.append([x,pair[0]/c,pair[1]/c])
        errors=[]
        for x,z in refs:
            pair=at(xle+c*x)
            if pair:errors.append(min(abs(z*c-pair[0]),abs(z*c-pair[1])))
        stations.append({"y_m":y,"chord_m":c,"max_thickness_c":max(p[2]-p[1] for p in samples),"max_camber_c":max((p[2]+p[1])/2 for p in samples),"source_point_max_deviation_mm":1000*max(errors),"source_points_matched":len(errors)})
        if y==0:plot=samples[::10]
    return {"file":name,"triangles":len(tris),"bounds_m":[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],"closed_two_faces_per_edge":all(n==2 for n in edges.values()),"edge_multiplicity":dict(collections.Counter(edges.values())),"volume_m3":abs(vol),"wetted_area_m2":area,"projected_planform_m2":areaXY,"stations":stations},plot
out={"method":"Independent sections and closed-edge checks of NX or STAR STL; metres; nominal chord and zero twist from unchanged NX expressions.","sources":{}}
plots={}
for filename,scale,refs in [("native_original_fine_mm.stl",.001,m["old_points"]),("native_012_fine_mm.stl",.001,m["new_points"]),("star_012_verified_m.stl",1.,m["new_points"])]:
    path=r/filename
    if not path.exists():continue
    result,plot=measure(read_stl(path,scale),filename,refs)
    out["sources"][filename]=result
    plots[filename]=plot
(r/"geometry_acceptance.json").write_text(json.dumps(out,indent=2))
(r/"section_plot_data.json").write_text(json.dumps(plots))
print(json.dumps(out,indent=2))
