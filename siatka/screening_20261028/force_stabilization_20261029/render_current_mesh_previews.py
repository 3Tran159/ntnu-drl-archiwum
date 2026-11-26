"""File-only cell-edge previews for current study; no STAR or source modifications."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import sys,json,hashlib,datetime,ctypes
sys.path.insert(0,'F:/ntnu/mesh_screening_20261028/quasi2d_012_20261029/deps311')
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
R=Path(__file__).resolve().parent
S=Path('C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/mesh_study_20261030/gci_w01a_20261030')
class Mem(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ('total','avail','page','availpage','virt','availvirt','extended')]
m=Mem();m.length=ctypes.sizeof(m)
if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)) or m.avail<8*1024**3:raise SystemExit('Insufficient spare memory for optional previews')
k=ctypes.windll.kernel32;k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
entries=[]
for name,source,sim in [
 ('M10',S/'handoff/mesh_star_export.CGNS',Path('E:/ntnu/quasi2d_waves_20261029/C01_W20L4_M10_FS020_mesh_r2/mesh.sim')),
 ('M11',S/'G10_M/mesh.CGNS',S/'G10_M/mesh.sim'),
 ('M12',S/'G10_F/mesh.CGNS',S/'G10_F/mesh.sim')]:
 before=digest(source)
 with h5py.File(source,'r') as f:
  zones=[];f.visititems(lambda n,o:zones.append(o) if isinstance(o,h5py.Group) and 'GridCoordinates' in o else None)
  if len(zones)!=1:raise ValueError('Expected one zone')
  z=zones[0];xz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in ('X','Z')])
  g=z['Q2D_span_source'];off=g['ElementStartOffset/ data'][...].astype(np.int64);con=g['ElementConnectivity/ data'][...].astype(np.int64)-1
  if off[0]!=0 or off[-1]!=len(con) or (np.diff(off)<3).any():raise ValueError('Invalid face connectivity')
  wall=z['HF_012_wall/ElementConnectivity/ data'][...].astype(np.int64)-1;foil=xz[wall]
  lo=foil.min(0);hi=foil.max(0);n=len(off)-1
  a=xz[con];mins=np.minimum.reduceat(a,off[:-1],axis=0);maxs=np.maximum.reduceat(a,off[:-1],axis=0);del a
 panels=[('Foil and near field',(lo[0]-.15,hi[0]+.2,lo[1]-.15,hi[1]+.15)),
         ('Leading edge',(lo[0]-.025,lo[0]+.12,lo[1]-.015,hi[1]+.015)),
         ('Trailing edge',(hi[0]-.12,hi[0]+.035,lo[1]-.015,hi[1]+.015)),
         ('Free-surface detail',(-.2,.2,1.85,2.15))]
 fig,axes=plt.subplots(2,2,figsize=(12.5,7.7),layout='constrained')
 for ax,(title,(xl,xh,zl,zh)) in zip(axes.ravel(),panels):
  ids=np.flatnonzero((maxs[:,0]>=xl)&(mins[:,0]<=xh)&(maxs[:,1]>=zl)&(mins[:,1]<=zh))
  polys=[xz[con[off[i]:off[i+1]]] for i in ids]
  ax.add_collection(PolyCollection(polys,facecolors='none',edgecolors='#486c78',linewidths=.25))
  ax.set(xlim=(xl,xh),ylim=(zl,zh),xlabel='x [m]',ylabel='z [m]',title=title)
  ax.set_aspect('equal',adjustable='box');ax.tick_params(labelsize=8)
  if 'surface' in title:ax.axhline(2,color='#1289a8',ls='--',lw=.8,label='Calm level z = 2 m');ax.legend(fontsize=8,loc='upper right')
 fig.suptitle(name+' | '+format(n,',')+' cells | actual single-span mesh',fontsize=14,color='#173138')
 output=R/(name+'_current_mesh_preview.png');fig.savefig(output,dpi=150);plt.close(fig)
 if digest(source)!=before:raise ValueError('Source changed during render')
 meta=dict(id=name,cells=n,source=str(source),source_sha256=before,source_unchanged=True,flow_steps=0,figure=str(output),figure_sha256=digest(output),generated_at=datetime.datetime.now().astimezone().isoformat(),method='Actual Q2D_span_source CGNS polygon edges; four fixed spatial crops. No interpolation or synthetic grid.',field_snapshot=False)
 receipt=R/(name+'_current_mesh_preview_provenance.json');receipt.write_text(json.dumps(meta,indent=2))
 entry=dict(id=name,audited=True,views=dict(mesh=dict(image_path=str(output),caption='Actual cell edges: foil, leading edge, trailing edge and free-surface band. Geometry preview only; no flow result.',provenance_file=str(receipt),source=str(source))))
 if sim.is_file():entry.update(sim_path=str(sim),sim_label='Prepared mesh .sim (no flow)')
 entries.append(entry)
 print(name,n,'rendered',flush=True)
 del xz,con,off,foil,mins,maxs,polys
manifest=R/'mesh_field_preview_manifest.json'
existing=json.loads(manifest.read_text()) if manifest.exists() else {'entries':[]}
byid={x['id']:x for x in existing.get('entries',[])}
for e in entries:
 old=byid.get(e['id'],{});views=old.get('views',{});views.update(e['views']);byid[e['id']]=dict(old,**{k:v for k,v in e.items() if k!='views'},views=views)
existing.update(entries=list(byid.values()),updated_at=datetime.datetime.now().astimezone().isoformat())
temp=manifest.with_suffix('.'+str(os.getpid())+'.tmp');temp.write_text(json.dumps(existing,indent=2));os.replace(temp,manifest)
print('Registered current mesh previews only; no solver launched.')
