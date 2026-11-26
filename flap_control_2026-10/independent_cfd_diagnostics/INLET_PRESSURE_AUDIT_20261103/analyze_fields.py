from pathlib import Path
import sys,json,hashlib
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'tools/deps'))
import numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D.mkdir(exist_ok=True)
paths={'065':H/'audit/relocation_native_20261103_C0/Background_reopened_volume.csv','069':H.parent/'independent_cfd_diagnostics/C0_speed_down_20261103/run_20261103_111057/Background_final_volume.csv','0706':H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103/run_20261103_113904/Background_failure_volume.csv'}
cols={'Pressure (Pa)':'p','Absolute Pressure (Pa)':'pabs','Volume (m^3)':'vol','Cell Quality':'q','Wall Distance (m)':'wall','Overset Cell Status':'status','Overset Cell Type':'type','Overset Error Status':'error','Overset Interpolation Type':'interpolation','Velocity[i] (m/s)':'u','Velocity[j] (m/s)':'v','Velocity[k] (m/s)':'w','X (m)':'x','Y (m)':'y','Z (m)':'z','Turbulent Kinetic Energy (J/kg)':'k','Specific Dissipation Rate (/s)':'omega'}
frames={k:pd.read_csv(p).rename(columns=cols) for k,p in paths.items()}
stats={};rho=1000.;g=9.8100004196167;pref=101325.;zref=2.;limit=12339.214766776897
for key,a in frames.items():
 a['hydro_abs']=pref+rho*g*(zref-a.z);a['identity_error']=a.pabs-a.p-a.hydro_abs
 idx=a.pabs.idxmin();row=a.loc[idx];low=a[a.pabs<=limit];inlet=a[a.x < -30]
 stats[key]=dict(rows=len(a),min_cell={k:float(row[k]) for k in ['x','y','z','p','pabs','hydro_abs','vol','q','wall','status','type','error','interpolation','u','v','w','k','omega']},min_cell_csv_data_row=int(idx)+1,identity_error_max_Pa=float(abs(a.identity_error).max()),bounds={axis:[float(a[axis].min()),float(a[axis].max())] for axis in ['x','y','z']},overset_status_counts={str(k):int(v) for k,v in a.status.value_counts().items()},below_threshold_cells=len(low),below_threshold_volume_m3=float(low.vol.sum()),below_threshold_bounds={axis:[float(low[axis].min()),float(low[axis].max())] if len(low) else None for axis in ['x','z']},inlet_region_cells=len(inlet),inlet_min_Pa=float(inlet.pabs.min()),inlet_pressure_quantiles=inlet.pabs.quantile([0,.01,.05,.5,.95,1]).to_dict())
 low.to_csv(D/('below_threshold_'+key+'.csv'),index=False)
 # Integer coordinate keys permit partition-order changes without interpolating the fields.
 a['kx']=(a.x*1e10).round().astype('int64');a['ky']=(a.y*1e10).round().astype('int64');a['kz']=(a.z*1e10).round().astype('int64')
 assert not a.duplicated(['kx','ky','kz']).any()
base=frames['065'];current=frames['0706'];previous=frames['069']
pair=current.merge(previous,on=['kx','ky','kz'],suffixes=('_end','_start'),validate='one_to_one').merge(base[['kx','ky','kz','p','u','w']],on=['kx','ky','kz'],validate='one_to_one');assert len(pair)==len(current)
pair['dp1']=pair.p_start-pair.p;pair['dp2']=pair.p_end-pair.p
def acceleration(t):
 x=(t-.65)/.4;return -20*30*x*x*(1-x)**2
a1=acceleration(.69);a2=acceleration(.706);ratio=a2/a1
fits={}
for name,mask in [('upstream',pair.x_end < -10),('inlet5m',pair.x_end < -30),('near_foil',abs(pair.x_end)<2)]:
 sub=pair[mask];x=sub.dp1.to_numpy();y=sub.dp2.to_numpy();coef=np.linalg.lstsq(np.column_stack([x,np.ones(len(x))]),y,rcond=None)[0];pred=coef[0]*x+coef[1]
 fits[name]=dict(cells=len(sub),fit_slope=float(coef[0]),intercept_Pa=float(coef[1]),R2=float(1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2)),rms_error_Pa=float(np.sqrt(np.mean((y-pred)**2))),predicted_acceleration_ratio=ratio,mean_u_change=float((sub.u_end-sub.u_start).mean()))
near=current.iloc[np.argsort((current.x-current.loc[current.pabs.idxmin(),'x'])**2+(current.z-current.loc[current.pabs.idxmin(),'z'])**2)[:30]]
near.to_csv(D/'minimum_30_neighbors.csv',index=False)
hist=pd.read_csv(H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103/run_20261103_113904/history.csv');pressure=pd.read_csv(H/'cases/BOUNDED_FIXED_PLUS2_SWEEP_20261103/run_20261103_113904/pressure_zones.csv')
hist['dU_dt_m_s2']=[acceleration(t) for t in hist.time_s];hist.to_csv(D/'time_history_audited.csv',index=False)
stats.update(accelerations=dict(t069=a1,t0706=a2,ratio=ratio),pressure_increment_fits=fits,neighbors=dict(count=30,pabs_min=float(near.pabs.min()),pabs_max=float(near.pabs.max()),below_threshold=int((near.pabs<limit).sum()),statuses=near.status.unique().tolist()),coordinate_match_count=len(pair))
(D/'FIELD_AUDIT.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
# Native cell-centre scatter plots avoid creating unsupported interpolated extrema.
fig,axs=plt.subplots(2,3,figsize=(15,9),constrained_layout=True)
for j,(key,label) in enumerate([('065','t=0.650s'),('069','t=0.690s'),('0706','t=0.706s')]):
 a=frames[key];sub=a[a.x<-20];vmin,vmax=0,350
 im=axs[0,j].scatter(sub.x,sub.z,c=sub.pabs/1000,s=14,cmap='viridis',vmin=vmin,vmax=vmax);axs[0,j].set_title(label+' pABS [kPa]')
 im2=axs[1,j].scatter(sub.x,sub.z,c=sub.p/1000,s=14,cmap='coolwarm',vmin=-200,vmax=20);axs[1,j].set_title('Deviation from hydrostatics / Pressure [kPa]')
 for ax in axs[:,j]:ax.set(xlabel='x [m]',ylabel='z [m]');ax.grid(alpha=.2)
fig.colorbar(im,ax=axs[0,:],label='kPa');fig.colorbar(im2,ax=axs[1,:],label='kPa');fig.savefig(D/'inlet_maps.png',dpi=160);plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
sub=pair[pair.x_end<-10];axs[0,0].scatter(sub.dp1/1000,sub.dp2/1000,s=4,alpha=.3);lims=[sub.dp1.min()/1000,sub.dp1.max()/1000];axs[0,0].plot(lims,np.array(lims)*ratio,'r--',label='dU/dt ratio');axs[0,0].set(xlabel='ΔPressure0.690−0.650 [kPa]',ylabel='ΔPressure0.706−0.650 [kPa]',title='Upstream pressure scales with acceleration');axs[0,0].legend()
for zone in ['fixed','flap','gap','liquid_all']:
 z=pressure[pressure.zone==zone];axs[0,1].plot(z.time_s,z.pabs_Pa/1000,'o-',label=zone)
axs[0,1].axhline(limit/1000,color='r',ls='--');axs[0,1].set(xlabel='time [s]',ylabel='pABS min [kPa]');axs[0,1].legend()
axs[1,0].plot(hist.time_s,hist.U_m_s,'o-',label='U');twin=axs[1,0].twinx();twin.plot(hist.time_s,hist.dU_dt_m_s2,'r--',label='dU/dt');axs[1,0].set(xlabel='time [s]',ylabel='U [m/s]');twin.set_ylabel('dU/dt [m/s²]',color='r')
axs[1,1].semilogy(hist.time_s,hist.mass_imbalance_relative,'o-',label='mass relative');axs[1,1].axhline(1e-4,color='r',ls='--');axs[1,1].set(xlabel='time [s]',ylabel='mass imbalance');axs[1,1].legend()
fig.savefig(D/'pressure_mechanism.png',dpi=160);plt.close(fig)
print(json.dumps(stats,indent=2))
