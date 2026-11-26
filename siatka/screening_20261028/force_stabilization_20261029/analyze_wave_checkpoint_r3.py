import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,csv,math,hashlib,datetime
from pathlib import Path
R=Path(__file__).resolve().parent;Q=R.parent/'quasi2d_012_20261029';sys.path.insert(0,str(Q/'deps311'))
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
A=Path('E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_flatOutlet_dt1ms_r3');P=A/'checkpoint_fields.csv'
with P.open() as f:raw=list(csv.DictReader(f))
data={k:np.array([float(x[k]) for x in raw]) for k in raw[0]}
assert all(np.isfinite(v).all() for v in data.values())
speed=data['Velocity: Magnitude (m/s)'];cfl=data['Convective Courant Number'];alpha=data['Volume Fraction of water'];x=data['X (m)'];z=data['Z (m)']
def cell(i):
 return {'x_m':float(x[i]),'z_m':float(z[i]),'speed_m_s':float(speed[i]),'u_x_m_s':float(data['Velocity[i] (m/s)'][i]),'u_z_m_s':float(data['Velocity[k] (m/s)'][i]),'alpha_water':float(alpha[i]),'pressure_Pa':float(data['Pressure (Pa)'][i]),'CFL':float(cfl[i]),'distances_m':{'inlet':float(x[i]+35),'outlet':float(45-x[i]),'top':float(8-z[i]),'bottom':float(z[i]+22),'forcing_end_x_minus15':float(abs(x[i]+15)),'damping_start_x25':float(abs(x[i]-25))}}
vmax=int(np.argmax(speed));cmax=int(np.argmax(cfl))
phases={}
for name,mask in [('water',alpha>=.99),('interface',(alpha>.01)&(alpha<.99)),('air',alpha<=.01)]:
 ids=np.where(mask)[0]
 phases[name]={'cells':len(ids),'max_speed_cell':cell(ids[np.argmax(speed[ids])]),'speed_p99_m_s':float(np.percentile(speed[ids],99)),'max_CFL':float(cfl[ids].max())}
counts={str(limit):{'total':int(np.sum(speed>limit)),'water':int(np.sum((speed>limit)&(alpha>=.99))),'interface':int(np.sum((speed>limit)&(alpha>.01)&(alpha<.99))),'air':int(np.sum((speed>limit)&(alpha<=.01)))} for limit in [20,25,30,40,50]}
out={'updated_at':datetime.datetime.now().astimezone().isoformat(),'time_s':.850,'status':'spatial_diagnostic_not_wave_acceptance','source':str(P),'source_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'all_fields_finite':True,'max_speed':cell(vmax),'max_CFL':cell(cmax),'phases':phases,'speed_threshold_counts':counts,'top_speed_cells':[cell(i) for i in np.argsort(speed)[-10:][::-1]]}
(R/'wave_pilot_r3_spatial_diagnostic.json').write_text(json.dumps(out,indent=2))
fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
for ax in axes:
 art=ax.scatter(x,z,c=speed,s=2,cmap='viridis',vmin=0,vmax=55,rasterized=True)
 ax.axvline(-15,color='white',ls='--',lw=.8);ax.axvline(25,color='white',ls='--',lw=.8)
 ax.set_xlabel('x [m]');ax.set_ylabel('z [m]')
axes[0].set(xlim=(-35,45),ylim=(-22,8),title='No-foil pilot: speed at the stability stop, t = 0.850 s')
axes[1].set(xlim=(max(-35,x[vmax]-5),min(45,x[vmax]+5)),ylim=(max(-22,z[vmax]-2),min(8,z[vmax]+2)),title='Local view around the maximum-speed cell')
for ax in axes:ax.plot(x[vmax],z[vmax],'rx',ms=8,mew=1.5)
fig.colorbar(art,ax=axes,label='Speed [m/s]')
fig.savefig(R/'wave_pilot_r3_spatial_diagnostic.png',dpi=160);plt.close(fig)
print(json.dumps({k:out[k] for k in ['max_speed','max_CFL','phases','speed_threshold_counts']},indent=2))
