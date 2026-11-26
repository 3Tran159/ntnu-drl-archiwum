from pathlib import Path
import json,math,csv,hashlib,shutil
from collections import defaultdict
R=Path(__file__).resolve().parent
V=json.loads(Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_poc_2606_20261102/audit/profile_vertices.json').read_text())
counts=defaultdict(int)
def key(v):return (round(v[0],7),round(v[2],7))
ymin=min(v[1] for v in V)
for k in range(0,len(V),3):
 tri=V[k:k+3]
 if all(abs(p[1]-ymin)<1e-7 for p in tri):
  pp=list(map(key,tri))
  for a,b in zip(pp,pp[1:]+pp[:1]):
   if a!=b:counts[tuple(sorted((a,b)))]+=1
edges={e for e,n in counts.items() if n==1}
graph=defaultdict(set)
for a,b in edges:graph[a].add(b);graph[b].add(a)
assert all(len(v)==2 for v in graph.values()),'Profile edge topology not a closed loop'
start=min(graph);pts=[start];prev=None;cur=start
for k in range(len(graph)+1):
 nxt=next(v for v in graph[cur] if v!=prev)
 if nxt==start:break
 pts.append(nxt);prev,cur=cur,nxt
assert len(pts)==len(graph)
# Reduce tiny tessellation edges for a deliberately coarse demonstrator.
def area(p):return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2
if area(pts)<0:pts.reverse()
filtered=[]
for p in pts:
 if not filtered or math.dist(p,filtered[-1])>.002:filtered.append(p)
pts=filtered
xmin=min(p[0] for p in pts);xmax=max(p[0] for p in pts);chord=xmax-xmin
xh=xmin+.8*chord
zs=[]
for a,b in zip(pts,pts[1:]+pts[:1]):
 if min(a[0],b[0])<=xh<=max(a[0],b[0]) and a[0]!=b[0]:
  zs.append(a[1]+(b[1]-a[1])*(xh-a[0])/(b[0]-a[0]))
zh=(min(zs)+max(zs))/2
gap=.02*chord
def clip(poly,x,less):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=(a[0]<=x) if less else (a[0]>=x)
  ib=(b[0]<=x) if less else (b[0]>=x)
  if ia:out.append(a)
  if ia!=ib:
   t=(x-a[0])/(b[0]-a[0]);out.append((x,a[1]+t*(b[1]-a[1])))
 return out
import sys
sys.path.insert(0,str(R/'deps'))
from shapely.geometry import Polygon, Point, box
from shapely.affinity import rotate
profile=Polygon(pts)
radius=(max(zs)-min(zs))/2
clearance=.015*chord
aft=profile.intersection(box(xh,-10,10,10))
nose=Point(xh,zh).buffer(radius,quad_segs=16).intersection(box(-10,-10,xh,10))
flap_shape=aft.union(nose)
main_shape=profile.intersection(box(-10,-10,xh,10)).difference(Point(xh,zh).buffer(radius+clearance,quad_segs=16))
assert main_shape.geom_type=='Polygon' and flap_shape.geom_type=='Polygon'
from shapely.geometry.polygon import orient
main=list(orient(main_shape,sign=1).exterior.coords)[:-1]
flap=list(orient(flap_shape,sign=1).exterior.coords)[:-1]
separations=[main_shape.distance(rotate(flap_shape,d,origin=(xh,zh))) for d in range(-5,6)]
assert min(separations)>clearance*.7
(R/'audit/geometry_clearance.json').write_text(json.dumps(dict(radius_m=radius,radial_clearance_m=clearance,tested_deg=list(range(-5,6)),minimum_separation_m=min(separations),native_profile=True,shape_valid=main_shape.is_valid and flap_shape.is_valid),indent=2))
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def triangulate(poly):
 idx=list(range(len(poly)));out=[]
 for it in range(len(poly)**2):
  if len(idx)==3:out.append(tuple(idx));return out
  found=False
  for k in range(len(idx)):
   a,b,c=idx[k-1],idx[k],idx[(k+1)%len(idx)]
   if cross(poly[a],poly[b],poly[c])<=1e-14:continue
   def inside(p):return min(cross(poly[a],poly[b],p),cross(poly[b],poly[c],p),cross(poly[c],poly[a],p))>=-1e-13
   if any(inside(poly[j]) for j in idx if j not in (a,b,c)):continue
   out.append((a,b,c));idx.pop(k);found=True;break
  if not found:raise ValueError('Polygon triangulation failed')
 raise ValueError('Triangulation iteration limit')
def stl(poly,name):
 tris=[]
 # x,z CCW, cap y+ has normal -y for x-z CCW, so reverse cap.
 from shapely import constrained_delaunay_triangles
 for tri in constrained_delaunay_triangles(Polygon(poly)).geoms:
  pp=list(tri.exterior.coords)[:3]
  if area(pp)<0:pp.reverse()
  tris.append([(x,-.02,z) for x,z in pp])
  tris.append([(x,.02,z) for x,z in reversed(pp)])
 for a,b in zip(poly,poly[1:]+poly[:1]):
  A=(a[0],-.02,a[1]);B=(b[0],-.02,b[1]);C=(b[0],.02,b[1]);D=(a[0],.02,a[1])
  tris.extend([[A,C,B],[A,D,C]])
 # Verify closed edge topology independent of STL reader.
 counts=defaultdict(int)
 for t in tris:
  for a,b in zip(t,t[1:]+t[:1]):counts[tuple(sorted((a,b)))]+=1
 assert all(v==2 for v in counts.values())
 with (R/'geometry'/f'{name}.stl').open('w') as f:
  f.write('solid '+name+'\n')
  for t in tris:
   f.write('facet normal 0 0 0\nouter loop\n')
   for p in t:f.write('vertex '+' '.join(map(str,p))+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid '+name+'\n')
stl(main,'POC_Main');stl(flap,'POC_Flap')
meta=dict(chord_projection_m=chord,hinge_x_m=xh,hinge_z_m=zh,hinge_axis=[0,1,0],hinge_fraction=.8,gap_m=clearance,nose_radius_m=radius,span_m=.02,solid_span_m=.04,profile_points=len(pts),main_points=len(main),flap_points=len(flap),amplitude_deg=5,period_s=.2,geometry_scope='Native NACA 66-012 modified contour; rounded flap nose and matching hinge recess; 1.5% chord radial clearance; not hydrodynamically validated')
(R/'geometry/geometry.json').write_text(json.dumps(meta,indent=2))
(R/'geometry/profile_polygons.json').write_text(json.dumps(dict(main=main,flap=flap)))
src=Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_drl_20261102/01_reference/C01_original_copy.sim')
dest=R/'input_copy.sim'
if not dest.exists():shutil.copy2(src,dest)
print(json.dumps(meta,indent=2))
