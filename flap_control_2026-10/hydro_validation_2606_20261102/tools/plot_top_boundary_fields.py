from pathlib import Path
import sys,json,datetime,numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]);label=sys.argv[2]
assert (run/('residual_normalization_'+label+'.txt')).exists(),'Incomplete field export'
old=h/'cases/SP_C_split0_overset/c0_urans_continue_inner40_20261103_041433'
paths=[old/'Background_final_volume.csv',run/('Background_'+label+'_volume.csv')]
frames=[];stats=[]
for p in paths:
 f=pd.read_csv(p)
 if 'Overset Cell Status' in f:f=f[f['Overset Cell Status']==0]
 f=f[(f['X (m)']>10)&(f['X (m)']<43)&(f['Z (m)']>7)&(f['Z (m)']<8)].copy();frames.append(f)
 w=f['Volume (m^3)'];vx=f['Velocity[i] (m/s)'];vz=f['Velocity[k] (m/s)'];deficit=np.maximum(18-vx,0)
 stats.append(dict(file=str(p),cells=len(f),volume_m3=float(w.sum()),vx_mean=float(np.average(vx,weights=w)),vx_min=float(vx.min()),vz_rms=float(np.sqrt(np.average(vz*vz,weights=w))),uniform18_velocity_deviation_rms=float(np.sqrt(np.average((vx-18)**2+vz**2,weights=w))),pabs_min_Pa=float(f['Absolute Pressure (Pa)'].min()),piezometric_min_Pa=float(f['Pressure (Pa)'].min()),piezometric_max_Pa=float(f['Pressure (Pa)'].max()),deficit_volume_mean=float(np.average(deficit,weights=w)),deficit_x_centroid_m=float(np.average(f['X (m)'],weights=w*deficit))))
if label.startswith('step_'):
 native=pd.read_csv(run/'far_top_metrics.csv');row=native[native.step==int(label.split('_')[1])].iloc[0];assert abs(stats[1]['vx_mean']-row.vx_volume_mean_m_s)<1e-7,('Native/offline farband mismatch',stats[1],row.to_dict())
o=dict(at=datetime.datetime.now().astimezone().isoformat(),label=label,selection='Active Background volume cells,10<x<43,7<z<8; native far-band mean cross-checked against offline export',scientific_approved=False,baseline=stats[0],candidate=stats[1])
(run/('top_boundary_fields_'+label+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
sys.path.insert(0,str(h/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,3,figsize=(14,6),sharex=True,sharey=True)
cols=[('Velocity[i] (m/s)',1,'Streamwise velocity [m/s]',6,18.1,'viridis'),('Velocity[k] (m/s)',1,'Vertical velocity [m/s]',-1,1,'coolwarm'),('Pressure (Pa)',.001,'Piezometric pressure [kPa]',-20,5,'coolwarm')]
for r,(f,title) in enumerate(zip(frames,['Before: top Boundary Normal, t0.450s','After: top Extrapolated, '+label])):
 for c,(k,scale,caption,lo,hi,cmap) in enumerate(cols):
  ax=axes[r,c];p=ax.scatter(f['X (m)'],f['Z (m)'],c=f[k]*scale,s=15,marker='s',cmap=cmap,vmin=lo,vmax=hi);ax.set(xlim=(10,43),ylim=(7,8),xlabel='x [m]',title=caption if r==0 else '');ax.grid(alpha=.1);fig.colorbar(p,ax=ax,fraction=.047,pad=.02)
 axes[r,0].set_ylabel(title+'\nz [m]')
fig.suptitle('Remote top boundary: actual cell-centre fields on unchanged Background mesh\nUniform inflow18m/s; separate direction-only diagnostic, scientific HOLD',fontsize=11);fig.tight_layout();dest=h/'reports'/('C0_top_boundary_fields_'+label+'.png');fig.savefig(dest,dpi=160);plt.close(fig)
print(json.dumps(o,indent=2));print(dest)
