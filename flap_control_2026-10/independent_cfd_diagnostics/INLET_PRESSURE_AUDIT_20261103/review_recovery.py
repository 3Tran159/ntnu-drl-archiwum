"""Read-only evaluation of the single native verification; never launches CFD."""
from pathlib import Path
import json,hashlib,sys,re
import pandas as pd,numpy as np
H=Path(r'F:\ntnu\flap_control\hydro_validation_2606_20261102');D=Path(__file__).resolve().parent
P=H/'cases/INLET_PRESSURE_RECOVERY_20261103/run_20261103_120108'
status=json.loads((P/'status.json').read_text());hist=pd.read_csv(P/'history.csv');pr=pd.read_csv(P/'pressure_zones.csv');r=pd.read_csv(P/'residual_history.csv')
groups=r.groupby(['time_s','monitor']).residual.agg(['first','last','count']);groups['ratio']=groups['last']/groups['first'];ratios=groups['ratio'].unstack();ratios.to_csv(D/'recovery_residual_ratios.csv')
checked=ratios.drop(columns=['Y-momentum']);last25=checked.tail(25)
physical=dict(steps_50=len(hist)==50,correct_times=np.allclose(hist.time_s,.690+.002*np.arange(1,len(hist)+1),atol=1e-10),native_iterations=np.allclose(hist.native_iteration,12360+50*np.arange(1,len(hist)+1)),pressure=bool((hist.p_absolute_min_Pa>12339.214766776897).all()),mass=bool((hist.mass_imbalance_relative<1e-4).all()),turbulence=bool((hist.omega_floor_cells==0).all() and (hist.k_floor_cells==0).all() and (hist.max_turbulent_viscosity_ratio<99999).all()),overset=bool((hist.overset_error_cells==0).all()),mesh=bool((hist.min_volume_m3>0).all() and (hist.min_cell_quality>0).all() and (hist.min_face_validity>=.5).all()),pose=bool((hist.flap_angle_deg==0).all() and (abs(hist.center_error_m)<1e-7).all()),speed=bool((hist.max_speed_m_s<=180).all()),finite=bool(np.isfinite(hist.select_dtypes(include='number')).all().all()),all_residual_windows_50=bool((groups['count']==50).all()),last25_residuals=bool(len(last25)==25 and (last25<=.01).all().all()))
audit=(P/('full_audit_final.txt' if status['status']=='pressure_recovery_complete' else 'full_audit_failure.txt')).read_text()
physical['native_full_overset']=all(x in audit for x in ['total=333939','errors=0','difficult_interpolation=0','active=255350','inactive=77108','acceptors=1481'])
initial=json.loads((P/'preflight.json').read_text());physical['saved_fields_match']=bool(abs(initial['CL']-.3206861558619269)<1e-9 and abs(initial['CD']-.007155867131695475)<1e-9 and abs(initial['Mh']+11.778200215235007)<1e-7 and not initial['fields_reset'])
cp=json.loads((P/'latest_checkpoint.json').read_text());cpfile=Path(cp['path'])
with cpfile.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
physical['checkpoint_hash']=actual==cp['sha256'] and cpfile.stat().st_size==cp['bytes']
suffix='final' if status['status']=='pressure_recovery_complete' else 'failure'
bg=pd.read_csv(P/f'Background_{suffix}_volume.csv');fo=pd.read_csv(P/f'FlapOverset_{suffix}_volume.csv');allf=pd.concat([bg,fo],ignore_index=True)
ident=allf['Absolute Pressure (Pa)']-allf['Pressure (Pa)']-101325-1000*9.8100004196167*(2-allf['Z (m)'])
physical['pressure_identity']=bool(abs(ident).max()<1e-6)
old=json.loads((D/'FIELD_AUDIT.json').read_text())['0706']['min_cell'];dist=(bg['X (m)']-old['x'])**2+(bg['Z (m)']-old['z'])**2;ix=dist.idxmin();assert dist.loc[ix]<1e-20
minima=pr.groupby('zone').pabs_Pa.agg(['min','max','last']).to_dict('index')
row=hist.iloc[-1];result=dict(test_id='INLET_PRESSURE_RECOVERY_20261103_TEST',status='PASS' if all(physical.values()) and status['status']=='pressure_recovery_complete' else 'HOLD',checks=physical,native_status=status,checkpoint=cp,last_step=row.to_dict(),minima=minima,max_mass_relative=float(hist.mass_imbalance_relative.max()),all_test_residuals_pass=bool((checked<=.01).all().all()),last25_max_residual_ratios=last25.max().to_dict(),residual_nonpass_steps=int((~(checked<=.01).all(axis=1)).sum()),first_bad_residual_times=checked.index[~(checked<=.01).all(axis=1)].tolist(),old_failure_location_pressure_now_Pa=float(bg.loc[ix,'Absolute Pressure (Pa)']),pressure_identity_error_Pa=float(abs(ident).max()),initial_native_readback=initial,full_overset=audit.strip(),scientific_validation=False,static_measurement_eligible=False,full_campaign_started=False)
result['force_relative_first_step_change']={k:float((hist.iloc[0][col]-initial[src])/abs(initial[src])) for k,col,src in [('CL','CL_hydro','CL'),('CD','CD','CD'),('Mh','Mh_Nm','Mh')]}
# Velocity propagation: retain near-inlet and downstream ranges, no assumption of uniform U.
result['velocity_field']={name:dict(cells=len(a),mean_u_m_s=float(a['Velocity[i] (m/s)'].mean()),min_u_m_s=float(a['Velocity[i] (m/s)'].min()),max_u_m_s=float(a['Velocity[i] (m/s)'].max())) for name,a in [('first_inlet_layer',bg[bg['X (m)']<-34.9]),('inlet_5m',bg[bg['X (m)']<-30]),('upstream_near_foil',bg[(bg['X (m)']>-2)&(bg['X (m)']<-1)])]}
(D/'RECOVERY_RESULT.json').write_text(json.dumps(result,indent=2,default=lambda x:bool(x) if isinstance(x,np.bool_) else float(x)),encoding='utf8')
sys.path.insert(0,str(H/'tools/deps'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
for z in ['liquid_all','fixed','flap','gap','inlet']:
 a=pr[pr.zone==z];axs[0,0].plot(a.time_s,a.pabs_Pa/1000,label=z)
axs[0,0].axhline(12.3392147668,color='r',ls='--');axs[0,0].set(ylabel='pABS,min [kPa]',xlabel='t [s]');axs[0,0].legend(fontsize=8)
axs[0,1].plot(hist.time_s,hist.U_m_s);ax=axs[0,1].twinx();ax.plot(hist.time_s,hist.dU_dt_m_s2,c='r');axs[0,1].set(xlabel='t [s]',ylabel='U [m/s]');ax.set_ylabel('dU/dt [m/s2]',color='r')
for name in ['CL_hydro','CD','Mh_Nm']:axs[1,0].plot(hist.time_s,hist[name]/hist[name].iloc[0],label=name)
axs[1,0].set(xlabel='t [s]',ylabel='relative to first new step');axs[1,0].legend()
for col in checked:axs[1,1].semilogy(checked.index,checked[col],label=col)
axs[1,1].axhline(.01,color='r',ls='--');axs[1,1].set(xlabel='t [s]',ylabel='last / first inner residual');axs[1,1].legend(fontsize=8)
fig.savefig(D/'recovery_result.png',dpi=160);plt.close(fig)
print(json.dumps({k:v for k,v in result.items() if k not in ['last_step','initial_native_readback']},indent=2,default=lambda x:bool(x) if isinstance(x,np.bool_) else float(x)))
