from pathlib import Path
import sys,json,hashlib,shutil,datetime,re
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
a=h/'cases/SP_A_original_singlephase'
chain=[a/'steady_init_20261102_182100/smoke_20261102_183017',a/'stabilize_20261102_190626',a/'stabilize_20261102_190626/stabilize_20261102_191755',a/'stabilize_20261102_190626/stabilize_20261102_191755/stabilize_20261102_192904']
end=chain[-1];status=json.loads((end/'status.json').read_text());assert status['status']=='force_stabilization_passed'
all_frames=[]
for p in chain:
 d=pd.read_csv(p/'history.csv');assert d['cavitation_screen_pass'].all() and (d.min_volume_m3>0).all()
 d['segment']=p.name;all_frames.append(d)
df=pd.concat(all_frames,ignore_index=True);assert df.time_s.is_monotonic_increasing and not df.time_s.duplicated().any()
df.to_csv(a/'SP_A_complete_accepted_history.csv',index=False)
last=all_frames[-1].tail(25)
source=end/'checkpoint.sim';dest=a/'SP_A_singlephase_stabilized_2606.sim'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
else:shutil.copy2(source,dest)
summary=dict(case='SP_A_original_singlephase',status='force_stabilization_passed',static_angle_deg=0,cells=309441,saved_time_s=status['saved_time_s'],saved_dt_s=.002,accepted_physical_steps=len(df),last_window_seconds=.05,CL_mean=float(last.CL_hydro.mean()),CL_std=float(last.CL_hydro.std()),CD_mean=float(last.CD.mean()),CD_std=float(last.CD.std()),Fx_mean_N=float(last.Fx_N.mean()),Fz_mean_N=float(last.Fz_N.mean()),moment_mean_Nm=float(last.Mh_Nm.mean()),moment_surface='whole intact foil; not flap-only',pabs_min_all_accepted_Pa=float(df.p_absolute_min_Pa.min()),pabs_min_last_window_Pa=float(last.p_absolute_min_Pa.min()),cavitation_margin_min_Pa=float(df.cavitation_margin_Pa.min()),safety_reserve_min_Pa=float(df.safety_reserve_Pa.min()),mass_imbalance_max_last_window=float(last.mass_imbalance_relative.max()),yplus_mean_last=float(last.yplus_mean.iloc[-1]),yplus_max_last=float(last.yplus_max.iloc[-1]),CL_vs_C01_percent=float((last.CL_hydro.mean()/.31565950495122014-1)*100),CD_vs_C01_percent=float((last.CD.mean()/.007002316911710474-1)*100),checkpoint=str(dest),checkpoint_sha256=digest,source_result=str(end),history=str(a/'SP_A_complete_accepted_history.csv'),grid_independence_verified=False,time_step_independence_verified=False,force_stabilization_verified=True,training_approved=False,at=datetime.datetime.now().astimezone().isoformat())
(h/'validation/SP_A_stabilized_result.json').write_text(json.dumps(summary,indent=2))
fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True,constrained_layout=True)
for axis,key,label in zip(ax,['CL_hydro','CD','p_absolute_min_Pa'],['CL bez wyporu','CD','Minimum ciśnienia abs. [kPa]']):
 axis.plot(df.time_s,df[key]/(1000 if key=='p_absolute_min_Pa' else 1),color='#146c94',lw=1.5);axis.set_ylabel(label);axis.grid(alpha=.2);axis.axvline(.0644,color='#e49c22',ls='--',lw=1)
ax[2].axhline(12.3392147668,color='#b13d3d',ls=':',label='próg 12,339 kPa');ax[2].legend(loc='lower right');ax[-1].set_xlabel('Czas fizyczny [s]')
fig.suptitle('Oryginalny płat — jednofazowy SST URANS, 18 m/s\nTen sam zapisany stan; zmiana dt z 0,4 ms na 2 ms przy t = 0,0644 s',fontsize=13)
fig.savefig(h/'reports/SP_A_stabilized_history.png',dpi=160);plt.close(fig)
print(json.dumps(summary,indent=2))
