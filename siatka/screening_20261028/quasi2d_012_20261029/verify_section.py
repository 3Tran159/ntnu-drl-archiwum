import json,struct,math
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
raw=(r/"HF_012_constant_section_mm.stl").read_bytes();n=struct.unpack_from("<I",raw,80)[0]
assert len(raw)==84+50*n
vsum=0.;segs=[]
for i in range(n):
 v=struct.unpack_from("<12fH",raw,84+50*i);a,b,c=[v[j:j+3] for j in [3,6,9]]
 cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
 vsum+=sum(a[j]*cross[j] for j in range(3))/6
 pts=[]
 for p,q in [(a,b),(b,c),(c,a)]:
  if (p[1]-20)*(q[1]-20)<0:
   t=(20-p[1])/(q[1]-p[1]);pts.append((p[0]+t*(q[0]-p[0]),p[2]+t*(q[2]-p[2])))
 if len(pts)==2:segs.append(pts)
xs=[p[0] for s in segs for p in s];xmin,xmax=min(xs),max(xs);extent=xmax-xmin;chord=1190.0
th=[];cam=[]
for k in range(1,2000):
 x=xmin+chord*k/2000
 z=[]
 for a,b in segs:
  if min(a[0],b[0])<=x<=max(a[0],b[0]) and abs(a[0]-b[0])>1e-12:z.append(a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1]))
 if len(z)>=2:th.append((max(z)-min(z))/chord);cam.append((max(z)+min(z))/2/chord)
area=abs(vsum)*1e-9 # span = 1m
result={"method":"Native solid STL volume and transverse section y=20mm","chord_m":chord/1000,"x_extent_m":extent/1000,"chord_convention":"Nominal CAD/DAT chord, not x bounding-box width; cambered profile nose extends slightly ahead of nominal LE","max_tc":max(th),"max_camber_c":max(cam),"section_area_m2":area,"slice_volume_m3":area*.02,"expected_buoyancy_N":area*.02*1000*9.81,"source_triangles":n,"section_segments":len(segs)}
print(result)
assert abs(result["chord_m"]-1.19)<.0001
assert abs(result["max_tc"]-.12)<.0002
assert abs(result["max_camber_c"]-.025)<.0002
(r/"section_verified.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
