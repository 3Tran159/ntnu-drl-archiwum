"""Professor-facing accepted field figures; read-only to all simulation sources."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import sys,csv,json,hashlib,datetime
from pathlib import Path
R=Path(__file__).resolve().parent
Q=R.parent/'quasi2d_012_20261029'
sys.path.insert(0,str(Q/'deps311'))
import numpy as np,h5py,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.path import Path as MPath
from matplotlib.colors import TwoSlopeNorm
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12.5,'axes.titlesize':14,'axes.labelsize':12.5,'xtick.labelsize':12,'ytick.labelsize':12,'svg.fonttype':'none','axes.linewidth':.7})
results=json.loads((R/'configured_mesh_results.json').read_text())['results']
snapshots={v['mesh']:{'status':'settled','time_s':v['window'][1],'velocity':str(Path(v['source_sim']).parent/'velocity_vectors.csv'),'history':str(Path(v['source_sim']).parent/'history.csv')} for v in results}
meshes=list(snapshots)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def geometry(mesh):
    with h5py.File(Q/mesh/'mesh.CGNS','r') as f:
        z=f['Base/fluid']
        xyz=np.column_stack([z['GridCoordinates/Coordinate'+a+'/ data'][...] for a in 'XYZ'])
        g=z['HF_012_wall'];con=g['ElementConnectivity/ data'][...]-1;off=g['ElementStartOffset/ data'][...];adj={}
        for i in range(len(off)-1):
            v=[int(k) for k in con[off[i]:off[i+1]] if abs(xyz[k,1]-.01)<1e-7]
            if len(v)==2:
                a,b=v;adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
        assert all(len(v)==2 for v in adj.values()),'Nonclosed foil boundary'
        start=min(adj,key=lambda k:xyz[k,0]);chain=[start];prev=None;cur=start
        while True:
            nxt=next(k for k in adj[cur] if k!=prev)
            if nxt==start:break
            chain.append(nxt);prev,cur=cur,nxt
            if len(chain)>len(adj):raise RuntimeError('Foil boundary loop failed')
        assert len(chain)==len(adj),'Multiple foil boundary loops'
        return xyz[chain][:,[0,2]]
def load(mesh):
    s=snapshots[mesh]
    assert s['status'].lower()=='settled',mesh+' is not accepted'
    p=Path(s['velocity'])
    with p.open(newline='') as f:
        rr=list(csv.DictReader(f))
    a={key:np.array([float(row[key]) for row in rr]) for key in rr[0]}
    assert all(np.all(np.isfinite(v)) for v in a.values()),mesh+' field contains nonfinite data'
    with Path(s['history']).open(newline='') as f:last=list(csv.DictReader(f))[-1]
    assert abs(float(last['physical_time_s'])-s['time_s'])<1e-8,'Saved timestamp mismatch'
    x=a['X (m)'];z=a['Z (m)'];poly=geometry(mesh);body=MPath(np.vstack([poly,poly[0]]),closed=True)
    keep=(x>-.65)&(x<3.2)&(z>-.8)&(z<.8)
    xp,zp=x[keep],z[keep];tri=mtri.Triangulation(xp,zp)
    pts=np.column_stack([xp,zp]);tt=pts[tri.triangles]
    mask=body.contains_points(tt.mean(axis=1))
    for i,j in [(0,1),(1,2),(2,0)]:mask|=body.contains_points((tt[:,i]+tt[:,j])*.5)
    tri.set_mask(mask)
    gx=np.linspace(-.35,2.7,850);gz=np.linspace(-.42,.44,300);xx,zz=np.meshgrid(gx,gz)
    solid=body.contains_points(np.column_stack([xx.ravel(),zz.ravel()])).reshape(xx.shape)
    def field(values):
        v=mtri.LinearTriInterpolator(tri,values[keep])(xx,zz)
        return np.ma.masked_where(solid|np.ma.getmaskarray(v),v)
    ux=field(a['Velocity[i] (m/s)']);uz=field(a['Velocity[k] (m/s)'])
    speed=field(np.sqrt(a['Velocity[i] (m/s)']**2+a['Velocity[j] (m/s)']**2+a['Velocity[k] (m/s)']**2))
    cp=field((a['Pressure (Pa)']-1000*9.81*(2-z))/(.5*1000*18**2))
    def clipped(v,lo,hi):
        vv=v.compressed()
        return {'below_percent':float(100*np.mean(vv<lo)),'above_percent':float(100*np.mean(vv>hi))}
    meta={'mesh':mesh,'status':s['status'],'time_s':s['time_s'],'source_cells':len(rr),'source':str(p),'source_sha256':sha(p),'mesh_file':str(Q/mesh/'mesh.CGNS'),'mesh_sha256':sha(Q/mesh/'mesh.CGNS'),'history':s['history'],'max_abs_spanwise_velocity_m_s':float(abs(a['Velocity[j] (m/s)']).max()),'display_grid_clipping':{'speed':clipped(speed,0,23),'Cp':clipped(cp,-.8,2.5)}}
    return {'gx':gx,'gz':gz,'xx':xx,'zz':zz,'ux':ux,'uz':uz,'speed':speed,'cp':cp,'poly':poly,'meta':meta}
data={m:load(m) for m in meshes}
def plotrow(axes,mesh):
    d=data[mesh];s=snapshots[mesh]
    im=axes[0].pcolormesh(d['xx'],d['zz'],d['speed'],cmap='viridis',vmin=0,vmax=23,shading='auto',rasterized=True)
    axes[0].streamplot(d['gx'],d['gz'],d['ux'],d['uz'],color='#ffffff',density=1.3,linewidth=.6,arrowsize=.8)
    im2=axes[1].pcolormesh(d['xx'],d['zz'],d['cp'],cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-.8,vcenter=0,vmax=2.5),shading='auto',rasterized=True)
    for ax in axes:
        ax.fill(d['poly'][:,0],d['poly'][:,1],color='#142e3d',zorder=10)
        ax.set(xlim=(-.35,2.7),ylim=(-.42,.44),xlabel='x [m]',ylabel='z [m]')
        ax.set_aspect('equal');ax.set_xticks([0,.5,1,1.5,2,2.5]);ax.set_yticks([-.4,0,.4])
        ax.tick_params(length=3)
    axes[0].set_title(mesh+'  |  t = '+format(s['time_s'],'.3f')+' s  |  Speed and streamlines',loc='left',pad=9)
    axes[1].set_title(mesh+'  |  t = '+format(s['time_s'],'.3f')+' s  |  Pressure coefficient',loc='left',pad=9)
    return im,im2
fig,axes=plt.subplots(len(meshes),2,figsize=(15.4,3.55*len(meshes)),layout='constrained',squeeze=False)
for i,m in enumerate(meshes):im,im2=plotrow(axes[i],m)
fig.colorbar(im,ax=list(axes[:,0]),label='Speed [m/s]',shrink=.82,pad=.015,fraction=.035,ticks=[0,5,10,15,20,23])
fig.colorbar(im2,ax=list(axes[:,1]),label='Cp',shrink=.82,pad=.015,fraction=.035,ticks=[-.8,0,.5,1,1.5,2,2.5])
fig.suptitle('Second-order calm screen | 1 ms, 10 inner iterations | Accepted instantaneous states',fontsize=16)
fig.savefig(R/'configured_fields.png',dpi=180);fig.savefig(R/'configured_fields.svg');plt.close(fig)
outputs=['configured_fields.png','configured_fields.svg']
for m in meshes:
    fig,axes=plt.subplots(1,2,figsize=(15.4,3.55),layout='constrained')
    im,im2=plotrow(axes,m)
    fig.colorbar(im,ax=axes[0],label='Speed [m/s]',pad=.018,fraction=.045,ticks=[0,10,20,23])
    fig.colorbar(im2,ax=axes[1],label='Cp',pad=.018,fraction=.045,ticks=[-.8,0,1,2.5])
    for suffix in ['png','svg']:
        out='configured_fields_'+m+'.'+suffix
        fig.savefig(R/out,**({'dpi':180} if suffix=='png' else {}));outputs.append(out)
    plt.close(fig)
provenance={'generated_at':datetime.datetime.now().astimezone().isoformat(),'outputs':outputs,'meshes':{m:data[m]['meta'] for m in meshes},'method':'Same display method as audited plot_flow_fields.py. Zero solver steps. Delaunay interpolation of saved cell-centred x-z fields; triangles sampled in solid interior masked and foil polygon overlaid from CGNS connectivity. Instantaneous 2D streamlines, not particle paths.','solver_configuration':{'time_order':'SECOND_ORDER','dt_s':.001,'inner':10},'field_type':'Instantaneous accepted saved states, not time-averaged fields. Force tables use separate final-window means.','pressure_definition':'Cp = [p - rho*g*(waterline_z-z)]/(0.5*rho*U^2), with rho=1000 kg/m^3, g=9.81 m/s^2, waterline_z=2 m, U=18 m/s. Nominal hydrostatic pressure is subtracted.','common_colour_limits':{'speed_m_s':[0,23],'Cp':[-.8,2.5]},'view_m':{'x':[-.35,2.7],'z':[-.42,.44]},'font_pt':{'body':12.5,'ticks':12,'titles':14}}
(R/'configured_fields_provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print(json.dumps({'outputs':outputs,'meshes':{m:{'time_s':data[m]['meta']['time_s'],'source_cells':data[m]['meta']['source_cells'],'clipping':data[m]['meta']['display_grid_clipping']} for m in meshes}}))
