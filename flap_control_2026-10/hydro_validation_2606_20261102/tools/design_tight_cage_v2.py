from pathlib import Path
import sys,json,math,hashlib,datetime
from collections import Counter,defaultdict
h=Path(__file__).resolve().parents[1]
sys.path.insert(0,'F:/ntnu/flap_control/flap_poc_2606_20261102/deps')
sys.path.insert(0,str(h/'tools/deps'))
import numpy as np
from shapely.geometry import Polygon,Point
from shapely.geometry.polygon import orient
from shapely.affinity import rotate
from shapely import constrained_delaunay_triangles
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
src=h/'geometry/gap_002500um';g=json.loads((src/'geometry.json').read_text(encoding='utf8'))
original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.stl')}
out=h/'geometry/c0_tight_cage_v2';out.mkdir(exist_ok=False)
xh,zh=g['hinge_x_m'],g['hinge_z_m'];rf=g['nose_radius_m'];rr=rf+g['gap_m']/2
main=Polygon(g['main_polygon']);flap=Polygon(g['flap_polygon'])
arc=[(xh+rr*math.cos(t),zh+rr*math.sin(t)) for t in np.linspace(math.pi/2,3*math.pi/2,129)]
points=arc+[(xh+.08,zh-.14),(1.55,zh-.28),(1.55,zh+.28),(xh+.08,zh+.14)]
cage=orient(Polygon(points),sign=1)
assert cage.is_valid and cage.covers(flap) and cage.intersection(main).area<1e-15
rows=[]
native_dir=h/'cases/SP_C_split0_overset/c0_layers36_recut_20261103_015428'
def nativepoly(name):
 data=json.loads((native_dir/(name+'_native_polygon.json')).read_text(encoding='utf8'))
 if isinstance(data,dict):print('NATIVE_KEYS',name,list(data));return None
 return Polygon(data)
native_main=nativepoly('main');native_flap=nativepoly('flap')
for angle in np.linspace(-5,5,101):
 rotated=rotate(cage,-float(angle),origin=(xh,zh))
 rotated_flap=rotate(flap,-float(angle),origin=(xh,zh))
 row=dict(angle_deg=float(angle),cage_main_distance_m=main.distance(rotated),cage_main_overlap_m2=main.intersection(rotated).area,flap_to_outer_boundary_m=rotated_flap.distance(rotated.boundary))
 if native_main is not None:
  row.update(native_main_clearance_m=native_main.distance(rotated),native_main_overlap_m2=native_main.intersection(rotated).area)
 rows.append(row)
assert min(r['cage_main_distance_m'] for r in rows)>.001
assert max(r['cage_main_overlap_m2'] for r in rows)<1e-15
assert flap.distance(cage.boundary)>.001
if native_main is not None:
 assert min(r['native_main_clearance_m'] for r in rows)>.001 and max(r['native_main_overlap_m2'] for r in rows)<1e-15
if native_flap is not None:assert cage.covers(native_flap) and native_flap.distance(cage.boundary)>.001
groups=defaultdict(list)
for tri in constrained_delaunay_triangles(cage).geoms:
 pp=list(orient(tri,sign=1).exterior.coords)[:3]
 groups['span_source'].append([(x,.01,z) for x,z in pp])
 groups['span_target'].append([(x,.03,z) for x,z in reversed(pp)])
poly=list(cage.exterior.coords)[:-1]
for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
 A=(a[0],.01,a[1]);B=(b[0],.01,b[1]);C=(b[0],.03,b[1]);D=(a[0],.03,a[1])
 patch='OversetArc' if i<128 else ['OversetLowerRamp','OversetLowerAft','OversetTrailing','OversetUpperAft','OversetUpperRamp'][i-128]
 groups[patch].extend([[A,C,B],[A,D,C]])
edges=Counter(tuple(sorted((a,b))) for tris in groups.values() for tri in tris for a,b in zip(tri,tri[1:]+tri[:1]))
assert all(n==2 for n in edges.values())
stl=out/'Hydro_TightCage.stl'
with stl.open('w') as f:
 for name,tris in groups.items():
  f.write('solid '+name+'\n')
  for tri in tris:
   f.write('facet normal 0 0 0\nouter loop\n')
   for v in tri:f.write('vertex '+' '.join(map(str,v))+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid '+name+'\n')
meta=dict(at=datetime.datetime.now().astimezone().isoformat(),purpose='Numerical Overset cage only; physical foil/flap/gap/span/hinge unchanged',hinge=[xh,.02,zh],nose_radius_m=rr,span_bounds_m=[.01,.03],cage_polygon=list(cage.exterior.coords),physical_geometry_sha256=original,cage_stl_sha256=hashlib.sha256(stl.read_bytes()).hexdigest(),triangles=sum(map(len,groups.values())),patch_triangles={k:len(v) for k,v in groups.items()},patch_change_only=True,angle_tests=rows,minimum_main_clearance_m=min(r['cage_main_distance_m'] for r in rows),minimum_flap_outer_clearance_m=min(r['flap_to_outer_boundary_m'] for r in rows),native_main_screened=native_main is not None,native_flap_screened=native_flap is not None,mesh_or_flow_run=False,scientific_approved=False)
assert original=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.stl')}
(out/'geometry_screen.json').write_text(json.dumps(meta,indent=2))
fig,ax=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
for a in ax:
 for body,label,col in [(main,'Fixed foil','#4c78a8'),(flap,'Flap','#59a14f')]:
  xy=np.array(body.exterior.coords);a.fill(xy[:,0],xy[:,1],color=col,alpha=.55,label=label)
 for ang in [-5,0,5]:
  xy=np.array(rotate(cage,-ang,origin=(xh,zh)).exterior.coords);a.plot(xy[:,0],xy[:,1],lw=1,label=f'Cage {ang:+d} deg')
 a.set_aspect('equal');a.set_xlabel('x [m]');a.set_ylabel('z [m]');a.grid(alpha=.2)
ax[0].set_xlim(.7,1.58);ax[0].set_ylim(-.3,.34);ax[0].legend(fontsize=8)
ax[1].set_xlim(xh-.05,xh+.012);ax[1].set_ylim(zh-.045,zh+.045)
fig.suptitle('Numerical cage clearance screen; physical geometry unchanged; no CFD approval')
fig.savefig(out/'cage_clearance.png',dpi=170);plt.close(fig)
reviewp=h/'WORK_CURRENT_REVIEW.json';v=json.loads(reviewp.read_text(encoding='utf8'))
v.update(at=meta['at'],mesh='Siatka źródłowa 579468 komórek: dodatnie objętości, zero błędów Overset. Lokalna ochrona 36 warstw + 1 warstwa na pozostałych ścianach zachowała wszystkie wierzchołki ścian i zero aktywnych środków komórek wewnątrz ciał. Pomiar w pięciu miejscach wykazał jednak brak odsunięcia interfejsu od ściany. Ten wariant nie usuwa wskazanego problemu.',next='Analiza i budowa osobnej kopii z ciaśniejszym obszarem Overset wokół klapki. Najpierw kontrola prześwitu geometrycznego, następnie siatki i łączności. Bez zmiany fizycznej geometrii i bez kolejnych wychyleń.',obstacle='Anomalie drugiego rzędu pędu przy interfejsie w warstwie przyściennej; rozbieżność sił 0° nadal niezatwierdzona.')
reviewp.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
with (h/'NIGHT_DECISIONS.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=meta['at'],kind='tight_cage_geometry_screen',path=str(out),min_main_clearance_m=meta['minimum_main_clearance_m'],min_flap_clearance_m=meta['minimum_flap_outer_clearance_m'],physical_geometry_unchanged=True,scientific_approved=False))+'\n')
print(json.dumps({k:v for k,v in meta.items() if k not in ('cage_polygon','angle_tests')},indent=2))
