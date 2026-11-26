from pathlib import Path
import json,math,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102\geometry\gap_002500um\geometry.json')
g=json.loads(SOURCE.read_text());c=1.19;hinge=np.array([.952,g['hinge_z_m']]);native=np.array(g['intact_polygon']);native=native[:-1] if np.linalg.norm(native[0]-native[-1])<1e-9 else native
# Keep every native vertex; explicitly insert the hinge crossings.
a=[]
for p,q in zip(native,np.roll(native,-1,axis=0)):
 if not a or np.linalg.norm(p-a[-1])>1e-9:a.append(p)
 if (p[0]-.952)*(q[0]-.952)<0:a.append(p+(.952-p[0])/(q[0]-p[0])*(q-p))
a=np.array(a)
def kernel(poly):
 k=[np.array(x) for x in [(-2,-2),(2,-2),(2,2),(-2,2)]]
 for p,q in zip(poly,np.roll(poly,-1,axis=0)):
  e=q-p;v=[]
  for u,w in zip(k,k[1:]+k[:1]):
   f=np.cross(e,u-p);h=np.cross(e,w-p)
   if f>=-1e-13:v.append(u)
   if (f>=0)!=(h>=0):v.append(u+f/(f-h)*(w-u))
  k=v
  if not k:raise ValueError('No star-shaped kernel; use unstructured mesher rather than accepting inverted cells')
 return np.mean(k,axis=0)
summary=[]
for deg in [0,2]:
 folder=ROOT/('delta_'+str(deg));folder.mkdir(exist_ok=True)
 theta=-math.radians(deg);rot=np.array([[math.cos(theta),-math.sin(theta)],[math.sin(theta),math.cos(theta)]])
 wall=[];tags=[]
 for p,q in zip(a,np.roll(a,-1,axis=0)):
  aft=(p[0]+q[0])/2>.952+1e-10
  pp=(p-hinge)@rot.T+hinge if aft else p;qq=(q-hinge)@rot.T+hinge if aft else q
  if wall and np.linalg.norm(wall[-1]-pp)>1e-9:tags.append('main');wall.append(pp)
  if not wall:wall.append(pp)
  tags.append('flap' if aft else 'main');wall.append(qq)
 if np.linalg.norm(wall[0]-wall[-1])<1e-9:wall.pop()
 else:tags.append('main')
 wall=np.array(wall);assert len(tags)==len(wall)
 center=kernel(wall);N=len(wall);NR=20
 # Ten near-wall layers (ratio1.2), ten graded outer bands; native foil retained.
 heights=np.array([.00015*1.2**k for k in range(10)]+[.01*2.0**k for k in range(10)])
 t=np.r_[0,np.cumsum(heights)/sum(heights)]
 vec=wall-center;outer=center+9.52*vec/np.linalg.norm(vec,axis=1)[:,None]
 nodes=np.array([wall+(outer-wall)*s for s in t]).reshape(-1,2)
 cells=[];areas=[];jac=[];faces={}
 for j in range(NR):
  for i in range(N):
   k=(i+1)%N;ids=[j*N+i,(j+1)*N+i,(j+1)*N+k,j*N+k];xy=nodes[ids];area=sum(np.cross(xy[(v+1)%4]-xy[v],xy[(v+2)%4]-xy[(v+1)%4]) for v in []) if False else .5*sum(np.cross(xy[v],xy[(v+1)%4]) for v in range(4));areas.append(area)
   for v in range(4):
    u=xy[(v+1)%4]-xy[v];w=xy[(v-1)%4]-xy[v];jac.append(float(np.cross(u,w)/(np.linalg.norm(u)*np.linalg.norm(w))))
   cells.append(ids);cid=len(cells)
   for u,v in zip(ids,ids[1:]+ids[:1]):
    key=tuple(sorted((u,v)))
    if key in faces:faces[key][3]=cid
    else:faces[key]=[u,v,cid,0]
 assert min(areas)>0 and min(jac)>0,(deg,min(areas),min(jac))
 zones={'interior':[],'main':[],'flap':[],'inlet':[],'outlet':[]}
 for u,v,c0,c1 in faces.values():
  if c1:zone='interior'
  elif u<N and v<N:
   i=v if (v+1)%N==u else u;zone=tags[i]
  else:zone='inlet' if (nodes[u,0]+nodes[v,0])/2<center[0] else 'outlet'
  zones[zone].append([u+1,v+1,c0,c1])
 def hx(x):return format(x,'x')
 with (folder/'mesh_2d.msh').open('w') as f:
  f.write('(0 "Native modified NACA; true 2D; closed hinge; delta='+str(deg)+'")\n(2 2)\n')
  f.write(f'(10 (0 1 {hx(len(nodes))} 0 2))\n(10 (1 1 {hx(len(nodes))} 1 2)(\n')
  for x,y in nodes:f.write(f'{x:.15g} {y:.15g}\n')
  f.write('))\n');f.write(f'(12 (0 1 {hx(len(cells))} 0))\n(12 (1 1 {hx(len(cells))} 1 3))\n')
  f.write(f'(13 (0 1 {hx(len(faces))} 0))\n');first=1
  for zid,(name,fs) in enumerate(zones.items(),2):
   bc={'interior':2,'main':3,'flap':3,'inlet':10,'outlet':5}[name];last=first+len(fs)-1
   f.write(f'(13 ({hx(zid)} {hx(first)} {hx(last)} {bc} 2)(\n')
   for row in fs:f.write(' '.join(hx(k) for k in row)+'\n')
   f.write('))\n');f.write(f'(45 ({zid} {"wall" if bc==3 else "velocity-inlet" if bc==10 else "pressure-outlet" if bc==5 else "interior"} {name})())\n');first=last+1
  f.write('(45 (1 fluid MINI_water)())\n')
 np.savetxt(folder/'foil_native_closed.csv',wall,delimiter=',',header='x_m,y_m',comments='')
 meta=dict(delta_deg=deg,cells=len(cells),nodes=len(nodes),min_area_m2=min(areas),min_scaled_corner_jacobian=min(jac),kernel_center=center.tolist(),source_vertices=len(native),foil_vertices=N,radial_layers=NR,geometry_source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),hinge_xy=hinge.tolist(),domain_radius_m=9.52,first_layer_fraction=float(t[1]),outer_layer_growth=2,warning='Coarse algebraic O-grid; first10 layers ratio1.2; wall rays not normal, especially trailing edge; native STAR quality check required; NOT grid validated',gap_model='Sealed hinge with short straight connectors; flap external aft skin only for Mh',true_2D=True)
 (folder/'geometry_mesh.json').write_text(json.dumps(meta,indent=2));summary.append(meta)
(ROOT/'PREPARED_MESHES.json').write_text(json.dumps(summary,indent=2));print(json.dumps([{k:v for k,v in x.items() if k in ['delta_deg','cells','min_area_m2','min_scaled_corner_jacobian','kernel_center']} for x in summary]))
