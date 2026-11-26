import sys,csv,json
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.path import Path as MPath
from matplotlib.collections import LineCollection
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
def geometry(mesh):
 with h5py.File(Q/mesh/'mesh.CGNS','r') as f:
  z=f['Base/fluid'];xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
  g=z['HF_012_wall'];con=g['ElementConnectivity/ data'][...]-1;off=g['ElementStartOffset/ data'][...];adj={}
  for i in range(len(off)-1):
   v=[int(k) for k in con[off[i]:off[i+1]] if abs(xyz[k,1]-.01)<1e-7]
   if len(v)==2:
    a,b=v;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
  start=min(adj,key=lambda k:xyz[k,0]);chain=[start];prev=None;cur=start
  while True:
   nxt=next(k for k in adj[cur] if k!=prev)
   if nxt==start:break
   chain.append(nxt);prev,cur=cur,nxt
   if len(chain)>len(adj):raise RuntimeError('Foil boundary loop failed')
  poly=xyz[chain][:,[0,2]]
  g=z['Q2D_span_source'];con=g['ElementConnectivity/ data'][...]-1;off=g['ElementStartOffset/ data'][...];edges=set()
  for i in range(len(off)-1):
   v=con[off[i]:off[i+1]]
   for a,b in zip(v,np.roll(v,-1)):edges.add(tuple(sorted((int(a),int(b)))))
  lines=xyz[np.array(list(edges))][:,:,[0,2]]
 return poly,lines
fig,axes=plt.subplots(2,2,figsize=(14,5.7),layout='constrained')
meshfig,ma=plt.subplots(2,3,figsize=(14,7),layout='constrained')
meta={}
for row,mesh in enumerate(['M02','M03']):
 p=R/(mesh+'_pilot_post')/'velocity_vectors.csv'
 if not (p.parent/'EXPORT_OK.json').exists():raise RuntimeError('Need completed vector export: '+mesh)
 with p.open() as f:rr=list(csv.DictReader(f))
 a={key:np.array([float(r[key]) for r in rr]) for key in rr[0]}
 x=a['X (m)'];z=a['Z (m)'];poly,lines=geometry(mesh);body=MPath(poly,closed=True)
 keep=(x>-.65)&(x<3.2)&(z>-.8)&(z<.8)
 xp,zp=x[keep],z[keep];tri=mtri.Triangulation(xp,zp)
 pts=np.column_stack([xp,zp]);tt=pts[tri.triangles]
 mask=body.contains_points(tt.mean(axis=1))
 for i,j in [(0,1),(1,2),(2,0)]:mask|=body.contains_points((tt[:,i]+tt[:,j])*.5)
 tri.set_mask(mask)
 gx=np.linspace(-.35,2.7,850);gz=np.linspace(-.42,.44,300);xx,zz=np.meshgrid(gx,gz);solid=body.contains_points(np.column_stack([xx.ravel(),zz.ravel()])).reshape(xx.shape)
 def field(values):
  v=mtri.LinearTriInterpolator(tri,values[keep])(xx,zz)
  return np.ma.masked_where(solid|np.ma.getmaskarray(v),v)
 ux=field(a['Velocity[i] (m/s)']);uz=field(a['Velocity[k] (m/s)'])
 speed=field(np.sqrt(a['Velocity[i] (m/s)']**2+a['Velocity[j] (m/s)']**2+a['Velocity[k] (m/s)']**2))
 cp=field((a['Pressure (Pa)']-1000*9.81*(2-z))/(.5*1000*18**2))
 im=axes[row,0].pcolormesh(xx,zz,speed,cmap='viridis',vmin=0,vmax=23,shading='auto',rasterized=True)
 axes[row,0].streamplot(gx,gz,ux,uz,color='#ffffff',density=1.5,linewidth=.52,arrowsize=.7)
 im2=axes[row,1].pcolormesh(xx,zz,cp,cmap='RdBu_r',norm=matplotlib.colors.TwoSlopeNorm(vmin=-.8,vcenter=0,vmax=2.5),shading='auto',rasterized=True)
 for ax in axes[row]:
  ax.fill(poly[:,0],poly[:,1],color='#172b39',zorder=10);ax.set(xlim=(-.35,2.7),ylim=(-.42,.44),xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal')
 axes[row,0].set_title(mesh+' - speed and instantaneous streamlines')
 axes[row,1].set_title(mesh+' - pressure coefficient field')
 meta[mesh]={'time_s':.2,'source_cells':len(rr),'source':str(p),'method':'Velocity components exported from saved STAR solution, with zero solver steps. Delaunay interpolation of cell-centred x-z fields for display. Triangles crossing sampled solid interior masked; foil polygon from CGNS connectivity. Instantaneous 2D streamlines, not particle paths.','max_abs_spanwise_velocity_m_s':float(abs(a['Velocity[j] (m/s)']).max())}
 limits=[(-.04,1.24,-.13,.16),(-.015,.065,-.032,.045),(1.12,1.205,-.035,.045)]
 for ax,lim,title in zip(ma[row],limits,['Foil and boundary layers','Leading edge','Trailing edge']):
  sel=(lines[:,:,0].min(axis=1)<lim[1])&(lines[:,:,0].max(axis=1)>lim[0])&(lines[:,:,1].min(axis=1)<lim[3])&(lines[:,:,1].max(axis=1)>lim[2])
  ax.add_collection(LineCollection(lines[sel],colors='#31546b',linewidths=.35));ax.fill(poly[:,0],poly[:,1],color='#dfe8ed')
  ax.set(xlim=lim[:2],ylim=lim[2:],title=mesh+' - '+title,xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal')
fig.colorbar(im,ax=list(axes[:,0]),label='Speed [m/s]',shrink=.8)
fig.colorbar(im2,ax=list(axes[:,1]),label='Cp, nominal hydrostatic pressure subtracted',shrink=.8)
fig.suptitle('Matched completed pilot snapshots | t = 0.2 s | U = 18 m/s\nInstantaneous streamlines from saved velocity vectors; common colour scales')
fig.savefig(R/'flow_streamlines_pressure.png',dpi=170);fig.savefig(R/'flow_streamlines_pressure.svg')
meshfig.suptitle('Actual quasi-2D meshes | one cell across the 0.02 m span')
meshfig.savefig(R/'mesh_detail_comparison.png',dpi=170);meshfig.savefig(R/'mesh_detail_comparison.svg')
(R/'flow_visualization_provenance.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta))
