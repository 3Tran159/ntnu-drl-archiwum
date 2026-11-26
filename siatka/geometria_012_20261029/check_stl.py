import json,math,hashlib,sys,struct,collections
from pathlib import Path
file=Path(sys.argv[1]);scale=float(sys.argv[2]);c=1.19
data=file.read_bytes()
if len(data)>=84 and len(data)==84+50*struct.unpack_from("<I",data,80)[0]:
    tris=[]
    for i in range(struct.unpack_from("<I",data,80)[0]):
        v=struct.unpack_from("<12fH",data,84+50*i)
        tris.append([tuple(scale*x for x in v[j:j+3]) for j in [3,6,9]])
else:
    pts=[tuple(scale*float(v) for v in l.split()[1:4]) for l in data.decode().splitlines() if l.split() and l.split()[0]=="vertex"]
    tris=[pts[i:i+3] for i in range(0,len(pts),3)]
pts=[p for t in tris for p in t]
segments=[]
for tri in tris:
    hits=[]
    for a,b in zip(tri,tri[1:]+tri[:1]):
        if abs(a[1]-b[1])<1e-12:continue
        u=-a[1]/(b[1]-a[1])
        if -1e-10<=u<=1+1e-10:
            p=(a[0]+u*(b[0]-a[0]),a[2]+u*(b[2]-a[2]))
            if not any(math.dist(p,h)<1e-9 for h in hits):hits.append(p)
    if len(hits)==2:segments.append(hits)
samples=[]
for i in range(1,2000):
    x=c*i/2000;zs=[]
    for (xa,za),(xb,zb) in segments:
        if abs(xb-xa)<1e-12:continue
        u=(x-xa)/(xb-xa)
        if -1e-9<=u<=1+1e-9:zs.append(za+u*(zb-za))
    if zs:samples.append({"x_over_c":x/c,"lower_m":min(zs),"upper_m":max(zs),"t_c":(max(zs)-min(zs))/c,"camber_c":(max(zs)+min(zs))/2/c})
result={"file":str(file),"sha256":hashlib.sha256(data).hexdigest(),"triangle_count":len(tris),"bounds_m":[[min(p[j] for p in pts),max(p[j] for p in pts)] for j in range(3)],"max_t":max(samples,key=lambda s:s["t_c"]),"max_camber":max(samples,key=lambda s:s["camber_c"])}
out=file.with_suffix(".section.json");out.write_text(json.dumps({"summary":result,"samples":samples},indent=2))
print(json.dumps(result,indent=2))
