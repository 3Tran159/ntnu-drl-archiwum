from pathlib import Path
import sys,json,numpy as np,hashlib,ctypes
R=Path(r'F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103');sys.path.insert(0,str(R.parent/'tools/deps'));import gmsh
k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t];k.SetProcessAffinityMask(k.GetCurrentProcess(),16)
D=R/'mini_vof_20261103';src=D/'SEALED0_A005';o=R/'mini_vof_20261103/NIGHT_20261103/FOIL_MESH';o.mkdir(exist_ok=True);gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(src/'geometry_and_mesh.msh'));ids,xyz,_=gmsh.model.mesh.getNodes();base=np.array(xyz).reshape(-1,3);nn=len(base);ix={int(t):i for i,t in enumerate(ids)};cells=[]
for typ,tags,ns in zip(*gmsh.model.mesh.getElements(2)):
 n=3 if typ==2 else 4 if typ==3 else 0;assert n
 for row in np.array(ns).reshape(-1,n):cells.append([ix[int(t)] for t in row])
edge_names={}
for dim,tag in gmsh.model.getPhysicalGroups(1):
 name=gmsh.model.getPhysicalName(1,tag)
 for curve in gmsh.model.getEntitiesForPhysicalGroup(1,tag):
  for ns in gmsh.model.mesh.getElements(1,curve)[2]:
   for a,b in np.array(ns).reshape(-1,2):edge_names[tuple(sorted((ix[int(a)],ix[int(b)])))]=name
gmsh.finalize();nodes=np.vstack([base,base+np.array([0,0,.02])]);faces={}
for cid,c in enumerate(cells,1):
 fs=[list(reversed(c)),[n+nn for n in c]]+[[u,v,v+nn,u+nn] for u,v in zip(c,c[1:]+c[:1])]
 for face in fs:
  key=tuple(sorted(face))
  if key in faces:assert faces[key][-1]==0;faces[key][-1]=cid
  else:faces[key]=face+[cid,0]
zones={n:[] for n in ['interior','main','flap','inlet','outlet','top','bottom','span_front','span_back']}
for key,face in faces.items():
 if face[-1]:name='interior'
 elif all(v<nn for v in key):name='span_front'
 elif all(v>=nn for v in key):name='span_back'
 else:name=edge_names[tuple(sorted(v for v in key if v<nn))]
 zones[name].append(face)
hx=lambda v:format(v,'x')
with (o/'mesh_3d.msh').open('w') as f:
 f.write('(0 "Sealed modified NACA source; one 20mm layer; preparation only")\n(2 3)\n');f.write(f'(10 (0 1 {hx(len(nodes))} 0 3))\n(10 (1 1 {hx(len(nodes))} 1 3)(\n');f.writelines(f'{x:.15g} {y:.15g} {z:.15g}\n' for x,y,z in nodes);f.write('))\n');f.write(f'(12 (0 1 {hx(len(cells))} 0))\n(12 (1 1 {hx(len(cells))} 1 0)(\n');f.write(' '.join('6' if len(c)==3 else '4' for c in cells));f.write('\n))\n');f.write(f'(13 (0 1 {hx(len(faces))} 0))\n');first=1
 for zid,(name,fs) in enumerate(zones.items(),2):
  bc=2 if name=='interior' else 3 if name in ['main','flap','bottom'] else 10 if name=='inlet' else 7 if name.startswith('span') else 5;last=first+len(fs)-1;ns={len(v)-2 for v in fs};ft=ns.pop() if len(ns)==1 else 0;f.write(f'(13 ({hx(zid)} {hx(first)} {hx(last)} {hx(bc)} {hx(ft)})(\n')
  for face0 in fs:
   face=list(reversed(face0[:-2]))+face0[-2:];f.write(('' if ft else hx(len(face)-2)+' ')+' '.join(hx(v+1) if i<len(face)-2 else hx(v) for i,v in enumerate(face))+'\n')
  f.write('))\n');f.write(f'(45 ({zid} '+{2:'interior',3:'wall',10:'velocity-inlet',5:'pressure-outlet',7:'symmetry'}[bc]+f' {name})())\n');first=last+1
 f.write('(45 (1 fluid MINI_water_air)())\n')
m=json.loads((src/'mesh_metadata.json').read_text());m.update(true_2D=False,quasi_2D=True,span_layers=1,span_m=.02,minimum_volume_m3=m['min_area_m2']*.02,expected_cells=len(cells),status='PREPARED_NATIVE_IMPORT_PENDING',solver_started=False,night_approved=False);(o/'mesh_metadata.json').write_text(json.dumps(m,indent=2));print(json.dumps(m))
