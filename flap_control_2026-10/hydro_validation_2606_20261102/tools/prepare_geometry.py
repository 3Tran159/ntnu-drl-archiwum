from pathlib import Path
from collections import defaultdict
import sys,json,math,argparse,hashlib,csv
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,'F:/ntnu/flap_control/flap_poc_2606_20261102/deps')
from shapely.geometry import Polygon,Point,box
from shapely.geometry.polygon import orient
from shapely.affinity import rotate
from shapely import constrained_delaunay_triangles
p=argparse.ArgumentParser();p.add_argument('--gap-mm',type=float,default=2.5);a=p.parse_args()
assert 1<=a.gap_mm<=20
V=json.loads(Path('F:/ntnu/flap_control/flap_poc_2606_20261102/audit/profile_vertices.json').read_text())
counts=defaultdict(int);ymin=min(v[1] for v in V)
def key(v):return (round(v[0],7),round(v[2],7))
for k in range(0,len(V),3):
 tri=V[k:k+3]
 if all(abs(v[1]-ymin)<1e-7 for v in tri):
  pts=list(map(key,tri))
  for x,y in zip(pts,pts[1:]+pts[:1]):
   if x!=y:counts[tuple(sorted((x,y)))]+=1
edges=[e for e,n in counts.items() if n==1]
graph=defaultdict(set)
for x,y in edges:graph[x].add(y);graph[y].add(x)
assert all(len(v)==2 for v in graph.values())
start=min(graph);pts=[start];prev=None;cur=start
for _ in range(len(graph)+1):
 nxt=next(v for v in graph[cur] if v!=prev)
 if nxt==start:break
 pts.append(nxt);prev,cur=cur,nxt
assert len(pts)==len(graph)
profile=orient(Polygon(pts),sign=1);pts=list(profile.exterior.coords)[:-1]
c=1.19;xh=.8*c;gap=a.gap_mm/1000
crossings=[]
for x,y in zip(pts,pts[1:]+pts[:1]):
 if min(x[0],y[0])<=xh<=max(x[0],y[0]) and x[0]!=y[0]:
  crossings.append(x[1]+(y[1]-x[1])*(xh-x[0])/(y[0]-x[0]))
zh=(max(crossings)+min(crossings))/2;radius=(max(crossings)-min(crossings))/2
nose=Point(xh,zh).buffer(radius,quad_segs=64).intersection(box(-10,-10,xh,10))
flap=orient(profile.intersection(box(xh,-10,10,10)).union(nose),sign=1)
main=orient(profile.intersection(box(-10,-10,xh,10)).difference(Point(xh,zh).buffer(radius+gap,quad_segs=64)),sign=1)
assert main.geom_type==flap.geom_type=='Polygon' and main.is_valid and flap.is_valid
angles=[-5+i*.1 for i in range(101)]
clearances=[main.distance(rotate(flap,-d,origin=(xh,zh))) for d in angles]
assert min(clearances)>.95*gap
folder=R/'geometry'/f'gap_{round(gap*1e6):06d}um';folder.mkdir(exist_ok=True)
def area(poly):return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2
def export(shape,name,arc_radius=None):
 poly=list(orient(shape,sign=1).exterior.coords)[:-1]
 groups=defaultdict(list)
 for tri in constrained_delaunay_triangles(shape).geoms:
  pp=list(tri.exterior.coords)[:3]
  if area(pp)<0:pp.reverse()
  groups['SpanCaps'].append([(x,0.,z) for x,z in pp])
  groups['SpanCaps'].append([(x,.04,z) for x,z in reversed(pp)])
 for x,y in zip(poly,poly[1:]+poly[:1]):
  arc=arc_radius is not None and x[0]<=xh+1e-7 and y[0]<=xh+1e-7 and all(abs(math.hypot(t[0]-xh,t[1]-zh)-arc_radius)<2e-5 for t in (x,y))
  group=('HingeArc' if arc else 'NativeSkin')
  A=(x[0],0.,x[1]);B=(y[0],0.,y[1]);C=(y[0],.04,y[1]);D=(x[0],.04,x[1])
  groups[group].extend([[A,C,B],[A,D,C]])
 edgecount=defaultdict(int)
 for triangles in groups.values():
  for tri in triangles:
   for x,y in zip(tri,tri[1:]+tri[:1]):edgecount[tuple(sorted((x,y)))]+=1
 assert all(n==2 for n in edgecount.values())
 with (folder/(name+'.stl')).open('w') as f:
  for label,triangles in groups.items():
   f.write('solid '+label+'\n')
   for tri in triangles:
    f.write('facet normal 0 0 0\nouter loop\n')
    for v in tri:f.write('vertex '+' '.join(map(str,v))+'\n')
    f.write('endloop\nendfacet\n')
   f.write('endsolid '+label+'\n')
 return {k:len(v) for k,v in groups.items()}
groups={name:export(shape,name,r) for name,shape,r in [('Hydro_Main',main,radius+gap),('Hydro_Flap',flap,radius),('Hydro_Intact',profile,None)]}
meta=dict(native_source='NACA 66-012 modified from protected native C01 geometry',nominal_chord_m=c,hinge_x_m=xh,hinge_z_m=zh,hinge_axis=[0,1,0],hinge_fraction=.8,gap_m=gap,nose_radius_m=radius,span_m=.02,boolean_tool_span_m=.04,native_profile_points=len(pts),main_polygon=list(main.exterior.coords),flap_polygon=list(flap.exterior.coords),intact_polygon=list(profile.exterior.coords),main_area_m2=main.area,flap_area_m2=flap.area,intact_area_m2=profile.area,min_clearance_m=min(clearances),tested_angle_step_deg=.1,parts_surface_triangle_counts=groups)
(folder/'geometry.json').write_text(json.dumps(meta,indent=2))
(R/'geometry/current_geometry.json').write_text(json.dumps(dict(folder=str(folder),**{k:v for k,v in meta.items() if not k.endswith('polygon')}),indent=2))
cfg=json.loads((R/'config.json').read_text())
n=[1167.0521452767,-724213.16703206,-17.073846940092,12020.82470247,-3232555.0322333,14.91510861353,-4823.2657361591,405113.40542057,-.23855557567849,650.17534844798]
T=cfg['temperature_C']+273.15;theta=T+n[8]/(T-n[9]);A=theta**2+n[0]*theta+n[1];B=n[2]*theta**2+n[3]*theta+n[4];C=n[5]*theta**2+n[6]*theta+n[7]
pv=(2*C/(-B+math.sqrt(B*B-4*A*C)))**4*1e6
cfg.update(p_vapor_Pa=pv,pressure_temperature_user_confirmed=True,p_vapor_method='IAPWS-IF97 region 4, equation 30',p_vapor_source='https://www.iapws.org/relguide/IF97-Rev.pdf')
(R/'config.json').write_text(json.dumps(cfg,indent=2))
print(json.dumps({k:v for k,v in meta.items() if not k.endswith('polygon')},indent=2))
print('P_VAPOR',pv,'ACCEPTANCE_ABSOLUTE_PRESSURE',pv+cfg['pressure_safety_margin_Pa'])
