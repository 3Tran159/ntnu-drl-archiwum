from pathlib import Path
import sys,json,hashlib,shutil,datetime
h=Path(__file__).resolve().parents[1];sys.path.insert(0,str(h/'tools/deps'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
variant=sys.argv[1];run=Path(sys.argv[2]).resolve();assert run.is_relative_to(h/'cases')
state=json.loads((run/'status.json').read_text());assert state['status']=='force_stabilization_passed'
meta=json.loads((run/'metadata.json').read_text());df=pd.read_csv(run/'history.csv');assert df.cavitation_screen_pass.all() and (df.min_volume_m3>0).all()
assert len(df)==state['steps'] and not df.select_dtypes('number').isna().any().any()
assert (df.time_s.diff().dropna()>0).all() and abs(df.time_s.iloc[-1]-state['saved_time_s'])<1e-8
assert (df.overset_error_cells==0).all() and (df.min_face_validity>.5).all() and (df.min_cell_quality>0).all()
assert (df.tail(75).mass_imbalance_relative<1e-4).all()
windows=[line.split(',') for line in (run/'force_windows.csv').read_text().splitlines() if line.strip()]
assert len(windows)>=3 and int(windows[-1][-1])>=3
last=df.tail(25);angle=meta.get('static_angle_deg',0)
assert (df.flap_angle_deg-angle).abs().max()<.01
folder=h/'cases'/('SP_B_split0_fixed' if variant=='SP_B' else 'SP_C_split0_overset')
name=variant+('_split0_stabilized_2606.sim' if angle==0 else f'_angle_{angle:+g}_stabilized_2606.sim')
source=run/'checkpoint.sim';dest=folder/name;sha=hashlib.sha256(source.read_bytes()).hexdigest()
if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
else:shutil.copy2(source,dest)
a=json.loads((h/'validation/SP_A_stabilized_result.json').read_text())
summary=dict(case=variant,static_angle_deg=angle,status=state['status'],cells=meta['cells'],saved_time_s=state['saved_time_s'],saved_dt_s=meta['dt_s'],physical_steps=len(df),last_window_seconds=.05,CL_mean=float(last.CL_hydro.mean()),CL_std=float(last.CL_hydro.std()),CD_mean=float(last.CD.mean()),CD_std=float(last.CD.std()),Fx_mean_N=float(last.Fx_N.mean()),Fz_mean_N=float(last.Fz_N.mean()),moment_mean_Nm=float(last.Mh_Nm.mean()),moment_surface='flap only, +y, total static pressure includes buoyancy',pabs_min_all_accepted_Pa=float(df.p_absolute_min_Pa.min()),pabs_min_last_window_Pa=float(last.p_absolute_min_Pa.min()),cavitation_margin_min_Pa=float(df.cavitation_margin_Pa.min()),safety_reserve_min_Pa=float(df.safety_reserve_Pa.min()),mass_imbalance_max_last_window=float(last.mass_imbalance_relative.max()),yplus_mean_last=float(last.yplus_mean.iloc[-1]),yplus_max_last=float(last.yplus_max.iloc[-1]),CL_vs_A_percent=float((last.CL_hydro.mean()/a['CL_mean']-1)*100),CD_vs_A_percent=float((last.CD.mean()/a['CD_mean']-1)*100),checkpoint=str(dest),checkpoint_sha256=sha,source_result=str(run),history=str(run/'history.csv'),grid_independence_verified=False,time_step_independence_verified=False,force_stabilization_verified=True,training_approved=False,at=datetime.datetime.now().astimezone().isoformat())
if variant=='SP_C':
 b=json.loads((h/'validation/SP_B_stabilized_result.json').read_text())
 summary.update(CL_vs_B_percent=float((last.CL_hydro.mean()/b['CL_mean']-1)*100),CD_vs_B_percent=float((last.CD.mean()/b['CD_mean']-1)*100))
if 'overset_error_cells' in df:summary.update(max_overset_error_cells=float(df.overset_error_cells.max()),max_difficult_interpolation_cells=float(df.difficult_interpolation_cells.max()))
suffix='' if angle==0 else f'_{angle:+g}'
(h/f'validation/{variant}_stabilized_result{suffix}.json').write_text(json.dumps(summary,indent=2))
fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True,constrained_layout=True)
for axis,key,label in zip(ax,['CL_hydro','CD','p_absolute_min_Pa'],['CL bez wyporu','CD','Minimum ciśnienia abs. [kPa]']):
 axis.plot(df.time_s,df[key]/(1000 if key=='p_absolute_min_Pa' else 1),color='#146c94',lw=1.5);axis.set_ylabel(label);axis.grid(alpha=.2)
ax[2].axhline(12.3392147668,color='#b13d3d',ls=':',label='próg 12,339 kPa');ax[2].legend(loc='lower right');ax[-1].set_xlabel('Czas fizyczny [s]');fig.suptitle(f'{variant}: klapka {angle:+g}° — SST URANS, 18 m/s\nStabilizacja sił w kolejnych oknach 0,05 s; dt = 2 ms',fontsize=13)
fig.savefig(h/f'reports/{variant}_stabilized_history{suffix}.png',dpi=160);plt.close(fig)
print(json.dumps(summary,indent=2))
