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
summary=[]
for variant,deg in [('gap',0),('gap',2),('sealed_demo',0)]:
 out=ROOT/f'{variant}_delta_{deg}';out.mkdir(exist_ok=True);t0=time.perf_counter();gmsh.initialize();gmsh.option.setNumber('General.NumThreads',1);gmsh.option.setNumber('General.Terminal',0);gmsh.model.add(out.name);geo=gmsh.model.geo;groups={n:[] for n in ['main','flap','inlet','outlet','farfield']};loops=[];wallcurves=[];gapcurves=[];fans=[]
 def poly(a,labels):
  points=[geo.addPoint(float(x),float(y),0) for x,y in a];edges=[geo.addLine(p,q) for p,q in zip(points,points[1:]+points[:1])]
  for i in range(len(a)):
   u=a[i]-a[i-1];v=a[(i+1)%len(a)]-a[i];turn=math.degrees(math.atan2(u[0]*v[1]-u[1]*v[0],float(u@v)))
   if turn>30:fans.append(points[i])
  for i,e in enumerate(edges):
   groups[labels[i]].append(e);wallcurves.append(e)
   mid=(a[i]+a[(i+1)%len(a)])/2
   if np.linalg.norm(mid-hinge)<.07:gapcurves.append(e)
  return geo.addCurveLoop(edges)
 if variant=='gap':
  main=clean(g['main_polygon']);flap=clean(g['flap_polygon']);th=-math.radians(deg);R=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]]);flap=(flap-hinge)@R.T+hinge
  loops=[poly(main,['main']*len(main)),poly(flap,['flap']*len(flap))]
 else:
  a,labels=sealed(deg);loops=[poly(a,labels)]
 dom=[(-5.95,-5.95),(11.9,-5.95),(11.9,5.95),(-5.95,5.95)];dp=[geo.addPoint(x,y,0,.45) for x,y in dom];de=[geo.addLine(p,q) for p,q in zip(dp,dp[1:]+dp[:1])];groups['farfield']=[de[0],de[2]];groups['outlet']=[de[1]];groups['inlet']=[de[3]];surface=geo.addPlaneSurface([geo.addCurveLoop(de)]+loops);geo.synchronize()
 for tag,(name,edges) in enumerate(groups.items(),1):gmsh.model.addPhysicalGroup(1,edges,tag);gmsh.model.setPhysicalName(1,tag,name)
 gmsh.model.addPhysicalGroup(2,[surface],20);gmsh.model.setPhysicalName(2,20,'MINI_water')
 fld=gmsh.model.mesh.field
 dist=fld.add('Distance');fld.setNumbers(dist,'CurvesList',wallcurves);fld.setNumber(dist,'Sampling',80)
 thr=fld.add('Threshold');fld.setNumber(thr,'InField',dist);fld.setNumber(thr,'SizeMin',.0025 if variant=='gap' else .009);fld.setNumber(thr,'SizeMax',.45);fld.setNumber(thr,'DistMin',.018 if variant=='gap' else .01);fld.setNumber(thr,'DistMax',1.0)
 fields=[thr]
 if variant=='gap':
  gd=fld.add('Distance');fld.setNumbers(gd,'CurvesList',gapcurves);fld.setNumber(gd,'Sampling',40);gt=fld.add('Threshold');fld.setNumber(gt,'InField',gd);fld.setNumber(gt,'SizeMin',.00025);fld.setNumber(gt,'SizeMax',.45);fld.setNumber(gt,'DistMin',.003);fld.setNumber(gt,'DistMax',.06);fields.append(gt)
 bg=fld.add('Min');fld.setNumbers(bg,'FieldsList',fields);fld.setAsBackgroundMesh(bg)
 bl=fld.add('BoundaryLayer');fld.setNumbers(bl,'CurvesList',wallcurves);fld.setNumber(bl,'Size',.00002 if variant=='gap' else .00002);fld.setNumber(bl,'Ratio',1.2);fld.setNumber(bl,'Thickness',.0009 if variant=='gap' else .0009);fld.setNumber(bl,'Quads',1);fld.setNumbers(bl,'FanPointsList',fans);fld.setAsBoundaryLayer(bl)
 gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0);gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0);gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0);gmsh.option.setNumber('Mesh.Algorithm',6)
 try:gmsh.model.mesh.generate(2)
 except Exception:
  (out/'meshing_error.txt').write_text('\n'.join(gmsh.logger.get()));gmsh.finalize();raise
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
   bc=2 if name=='interior' else 3 if name in ['main','flap'] else 10 if name=='inlet' else 5 if name=='outlet' else 7;last=first+len(fs)-1;f.write(f'(13 ({hx(zid)} {hx(first)} {hx(last)} {hx(bc)} 2)(\n');f.writelines(' '.join(hx(k) for k in row)+'\n' for row in fs);f.write('))\n');f.write(f'(45 ({zid} '+{2:'interior',3:'wall',10:'velocity-inlet',5:'pressure-outlet',7:'symmetry'}[bc]+f' {name})())\n');first=last+1
  f.write('(45 (1 fluid MINI_water)())\n')
 gmsh.write(str(out/'geometry_and_mesh.msh'));gmsh.write(str(out/'geometry.geo_unrolled'));gmsh.finalize();meta=dict(run_id=out.name,variant=variant,delta_deg=deg,cells=len(cells),min_area_m2=min(areas),min_SICN=float(min(qualities)),mesh_seconds=time.perf_counter()-t0,gap_m=.0025 if variant=='gap' else 0,true_2D=True,overset=False,VOF=False,first_layer_m=.00002 if variant=='gap' else .00002,layer_thickness_m=.0009 if variant=='gap' else .0009,gap_target_size_m=.00025 if variant=='gap' else None,source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),status='MESH_PREPARED_NATIVE_IMPORT_PENDING',fidelity='L1_GAP' if variant=='gap' else 'L1_SEALED_ALGORITHM_DEMONSTRATOR',static_next=[-5,-2,0,2,5],next_angles_require_previous_case_review=True,dynamic_planned_amplitudes=[2,5],DRL_5deg_approved=False);(out/'mesh_metadata.json').write_text(json.dumps(meta,indent=2));summary.append(meta);print(json.dumps(meta),flush=True)
(ROOT/'MINI_PREPARATION.json').write_text(json.dumps(summary,indent=2))
