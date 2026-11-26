from pathlib import Path
import sys,json,math,time,hashlib,ctypes
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'tools/deps'));import gmsh
SOURCE=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102\geometry\gap_002500um\geometry.json');g=json.loads(SOURCE.read_text());hinge=np.array([g['hinge_x_m'],g['hinge_z_m']])
k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];assert k.SetProcessAffinityMask(k.GetCurrentProcess(),1<<4)
def clean(a):
 b=[]
 for p in a:
  if not b or np.linalg.norm(np.array(p)-b[-1])>1e-8:b.append(np.array(p))
 if np.linalg.norm(b[0]-b[-1])<1e-8:b.pop()
 return np.array(b)
def sealed(deg):
 a=clean(g['intact_polygon']);pts=[];labels=[];th=-math.radians(deg);R=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]])
 for p,q in zip(a,np.roll(a,-1,axis=0)):
  if (p[0]-.952)*(q[0]-.952)<0:
   w=p+(.952-p[0])/(q[0]-p[0])*(q-p);segments=[(p,w),(w,q)]
  else:segments=[(p,q)]
  for u,v in segments:
   aft=(u[0]+v[0])/2>.952+1e-10;u=(u-hinge)@R.T+hinge if aft else u;v=(v-hinge)@R.T+hinge if aft else v
   if pts and np.linalg.norm(pts[-1]-u)>1e-8:labels.append('main');pts.append(u)
   if not pts:pts.append(u)
   labels.append('flap' if aft else 'main');pts.append(v)
 if np.linalg.norm(pts[0]-pts[-1])<1e-8:pts.pop()
 else:labels.append('main')
 return np.array(pts),labels

out=ROOT/'mini_vof_20261103'/'SEALED0_A005';out.mkdir(exist_ok=True);t0=time.perf_counter();gmsh.initialize();gmsh.option.setNumber('General.NumThreads',1);gmsh.option.setNumber('General.Terminal',0);gmsh.model.add('MINI_VOF_SEALED0');geo=gmsh.model.geo;variant='sealed_VOF_demo';sy=2.02128173276777;yb=sy-.4;yt=sy+.4
groups={n:[] for n in ['main','flap','inlet','outlet','top','bottom']};wallcurves=[];fans=[]
a,labels=sealed(0);foil_area=abs(.5*sum(a[i,0]*a[(i+1)%len(a),1]-a[i,1]*a[(i+1)%len(a),0] for i in range(len(a))))
p=[geo.addPoint(float(x),float(y),0) for x,y in a];edges=[geo.addLine(u,v) for u,v in zip(p,p[1:]+p[:1])]
for i,e in enumerate(edges):
 groups[labels[i]].append(e);wallcurves.append(e);u=a[i]-a[i-1];v=a[(i+1)%len(a)]-a[i];turn=math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0],float(u@v)))
 if turn>30:fans.append(p[i])
foil=geo.addCurveLoop(edges)
ys=[-10,yb,yt,4];lp=[geo.addPoint(-12,y,0) for y in ys];rp=[geo.addPoint(28,y,0) for y in ys];h=[geo.addLine(l,r) for l,r in zip(lp,rp)];le=[geo.addLine(lp[i],lp[i+1]) for i in range(3)];re=[geo.addLine(rp[i],rp[i+1]) for i in range(3)];sur=[]
for i in range(3):sur.append(geo.addPlaneSurface([geo.addCurveLoop([h[i],re[i],-h[i+1],-le[i]])]+([foil] if i==0 else [])))
groups['bottom']=[h[0]];groups['top']=[h[3]];groups['inlet']=le;groups['outlet']=re;geo.synchronize()
for i in [1,2,3]:gmsh.model.mesh.setTransfiniteCurve(h[i],321)
for side in [le,re]:gmsh.model.mesh.setTransfiniteCurve(side[1],65);gmsh.model.mesh.setTransfiniteCurve(side[2],25,'Progression',1.08)
for i in [1,2]:gmsh.model.mesh.setTransfiniteSurface(sur[i]);gmsh.model.mesh.setRecombine(2,sur[i])
for tag,(name,eds) in enumerate(groups.items(),1):gmsh.model.addPhysicalGroup(1,eds,tag);gmsh.model.setPhysicalName(1,tag,name)
gmsh.model.addPhysicalGroup(2,sur,20);gmsh.model.setPhysicalName(2,20,'MINI_water_air');fld=gmsh.model.mesh.field
dist=fld.add('Distance');fld.setNumbers(dist,'CurvesList',wallcurves);fld.setNumber(dist,'Sampling',80);thr=fld.add('Threshold');fld.setNumber(thr,'InField',dist);fld.setNumber(thr,'SizeMin',.009);fld.setNumber(thr,'SizeMax',.65);fld.setNumber(thr,'DistMin',.01);fld.setNumber(thr,'DistMax',1.0)
d=fld.add('Distance');fld.setNumbers(d,'CurvesList',[h[1]]);fld.setNumber(d,'Sampling',321);t=fld.add('Threshold');fld.setNumber(t,'InField',d);fld.setNumber(t,'SizeMin',.125);fld.setNumber(t,'SizeMax',.65);fld.setNumber(t,'DistMin',.05);fld.setNumber(t,'DistMax',1.5);bg=fld.add('Min');fld.setNumbers(bg,'FieldsList',[thr,t]);fld.setAsBackgroundMesh(bg)
bl=fld.add('BoundaryLayer');fld.setNumbers(bl,'CurvesList',wallcurves);fld.setNumber(bl,'Size',.00002);fld.setNumber(bl,'Ratio',1.2);fld.setNumber(bl,'Thickness',.0009);fld.setNumber(bl,'Quads',1);fld.setNumbers(bl,'FanPointsList',fans);fld.setAsBoundaryLayer(bl)
gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0);gmsh.option.setNumber('Mesh.Algorithm',6);gmsh.model.mesh.generate(2)
nodeids,xyz,_=gmsh.model.mesh.getNodes();nodes=np.array(xyz).reshape(-1,3);lookup={int(k):i for i,k in enumerate(nodeids)};cells=[];elementids=[]
types,ets,ens=gmsh.model.mesh.getElements(2)
for typ,ids,nn in zip(types,ets,ens):
 dim,n=gmsh.model.mesh.getElementProperties(typ)[1:4:2] if False else (2,3 if typ==2 else 4 if typ==3 else 0);assert n
 for eid,row in zip(ids,np.array(nn).reshape(-1,n)):cells.append([lookup[int(x)] for x in row]);elementids.append(int(eid))
qualities=gmsh.model.mesh.getElementQualities(elementids,'minSICN');print('QUALITY',float(min(qualities)),float(np.median(qualities)),int(sum(qualities<=0)),len(qualities),flush=True);gmsh.write(str(out/'precheck.msh'));assert min(qualities)>0
boundary={}
for name,curves in groups.items():
 for curve in curves:
  ts,ids,ns=gmsh.model.mesh.getElements(1,curve)
  for ns0 in ns:
   for u,v in np.array(ns0).reshape(-1,2):boundary[tuple(sorted((lookup[int(u)],lookup[int(v)])))]=name
faces={};areas=[]
for cid,cell in enumerate(cells,1):
 xy=nodes[cell,:2];area=.5*sum(xy[i,0]*xy[(i+1)%len(xy),1]-xy[i,1]*xy[(i+1)%len(xy),0] for i in range(len(xy)));assert area>0;areas.append(area)
 for u,v in zip(cell,cell[1:]+cell[:1]):
  key=tuple(sorted((u,v)))
  if key in faces:assert faces[key][3]==0;faces[key][3]=cid
  else:faces[key]=[u+1,v+1,cid,0]
zones={'interior':[]};zones.update({n:[] for n in groups})
for key,face in faces.items():zones['interior' if face[3] else boundary[key]].append(face)
hx=lambda n:format(n,'x')
with (out/'mesh_2d.msh').open('w') as f:
 f.write('(0 "True 2D MINI '+variant+'")\n(2 2)\n');f.write(f'(10 (0 1 {hx(len(nodes))} 0 2))\n(10 (1 1 {hx(len(nodes))} 1 2)(\n');f.writelines(f'{x:.15g} {y:.15g}\n' for x,y,z in nodes);f.write('))\n');f.write(f'(12 (0 1 {hx(len(cells))} 0))\n(12 (1 1 {hx(len(cells))} 1 0)(\n');f.write(' '.join('1' if len(x)==3 else '3' for x in cells));f.write('\n))\n');f.write(f'(13 (0 1 {hx(len(faces))} 0))\n');first=1
 for zid,(name,fs) in enumerate(zones.items(),2):
  bc=2 if name=='interior' else 3 if name in ['main','flap'] else 10 if name=='inlet' else 3 if name=='bottom' else 5;last=first+len(fs)-1;f.write(f'(13 ({hx(zid)} {hx(first)} {hx(last)} {hx(bc)} 2)(\n');f.writelines(' '.join(hx(k) for k in row)+'\n' for row in fs);f.write('))\n');f.write(f'(45 ({zid} '+{2:'interior',3:'wall',10:'velocity-inlet',5:'pressure-outlet',7:'symmetry'}[bc]+f' {name})())\n');first=last+1
 f.write('(45 (1 fluid MINI_water)())\n')
gmsh.write(str(out/'geometry_and_mesh.msh'));gmsh.finalize();meta=dict(cells=len(cells),min_SICN=float(min(qualities)),nonpositive_cells=int(sum(qualities<=0)),min_area_m2=min(areas),geometry='original modified NACA66-012 sealed demonstrator',gap_m=0,delta_deg=0,hinge=[.952,.02128173276777],hinge_submergence_m=2,foil_area_m2=foil_area,buoyancy_N_per_m=1000*9.81*foil_area,true_2D=True,VOF=True,mesh_seconds=time.perf_counter()-t0,source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),status='MESH_PREPARED_NATIVE_IMPORT_PENDING',wave_test_PASS_required=True,night_approved=False)
(out/'mesh_metadata.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta),flush=True)
