"""Evidence only: never approves results, modifies queue, or starts STAR."""
from pathlib import Path
import sys,json,datetime,re
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1]
run=Path(sys.argv[1]).resolve()
assert run.is_relative_to(h/'cases/SP_C_split0_overset')
d=pd.read_csv(run/'history.csv')
status=json.loads((run/'status.json').read_text(encoding='utf8')) if (run/'status.json').exists() else None
o=dict(at=datetime.datetime.now().astimezone().isoformat(),run=str(run),samples=len(d),last_time_s=float(d.time_s.iloc[-1]),macro_status=status,scientific_approved=False,training_approved=False)
o['whole_run_guards']=dict(pressure=bool((d.p_absolute_min_Pa>12339.214766776897).all()),volume=bool((d.min_volume_m3>0).all()),quality=bool((d.min_cell_quality>0).all()),face=bool((d.min_face_validity>.5).all()),overset_active_errors=bool((d.overset_error_cells==0).all()),angle_zero=bool((d.flap_angle_deg.abs()<.01).all()))
o['last']=d.iloc[-1].to_dict()
o['whole_run_guards']['mass']=bool((d.mass_imbalance_relative<1e-4).all())
for column in ['omega_floor_cells','k_floor_cells']:
 if column in d:o['whole_run_guards'][column]=bool((d[column]==0).all())
if 'max_turbulent_viscosity_ratio' in d:o['whole_run_guards']['viscosity_ratio']=bool((d.max_turbulent_viscosity_ratio<99999).all())
o['whole_run_guards']['finite_history']=bool(np.isfinite(d.select_dtypes(include=[np.number]).to_numpy()).all())
o['window_results']=[]
for end in range(25,len(d)+1,25):
 a=d.iloc[end-25:end];rec=dict(end_step=end,time_s=float(a.time_s.iloc[-1]),means={},relative_ranges={},mass_max=float(a.mass_imbalance_relative.max()),pabs_min=float(a.p_absolute_min_Pa.min()))
 for col in ['CL_hydro','CD','Mh_Nm','Fx_N','Fz_N']:
  rec['means'][col]=float(a[col].mean());rec['relative_ranges'][col]=float(np.ptp(a[col]))/max(1e-12,abs(float(a[col].mean())))
 if end>=50:
  prev=d.iloc[end-50:end-25];rec['relative_mean_change']={col:float(a[col].mean()/prev[col].mean()-1) for col in ['CL_hydro','CD','Mh_Nm']}
  rec['force_window_pass']=bool(rec['mass_max']<1e-4 and abs(rec['relative_mean_change']['CL_hydro'])<.005 and abs(rec['relative_mean_change']['CD'])<.01 and abs(rec['relative_mean_change']['Mh_Nm'])<.01 and rec['relative_ranges']['CL_hydro']<.01 and rec['relative_ranges']['CD']<.02 and rec['relative_ranges']['Mh_Nm']<.02)
 o['window_results'].append(rec)
a=d.tail(25)
o['last_25_means']={k:float(a[k].mean()) for k in ['CL_hydro','CD','Fx_N','Fz_N','Mh_Nm']}
o['delta_B_percent']={k:100*(o['last_25_means'][k]/v-1) for k,v in {'CL_hydro':.32729653634048,'CD':.007163580556642399}.items()}
for col in ['omega_floor_cells','k_floor_cells','max_turbulent_viscosity_ratio']:
 if col in d:o[col]=dict(first=float(d[col].iloc[0]),latest=float(d[col].iloc[-1]),last_25_min=float(a[col].min()),last_25_max=float(a[col].max()))
o['field_exports']={}
labels=sorted(set(re.match(r'Background_(.+)_volume.csv',p.name).group(1) for p in run.glob('Background_*_volume.csv')))
labels=[label for label in labels if (run/('residual_normalization_'+label+'.txt')).exists()] # captureComparison writes this completion marker after all field exports
for label in labels:
 frames=[]
 for region in ['Background','FlapOverset']:
  p=run/(region+'_'+label+'_volume.csv')
  if not p.exists():continue
  f=pd.read_csv(p);f=f[f['Overset Cell Status']==0].copy();f['region']=region;frames.append(f)
 if len(frames)!=2:continue
 f=pd.concat(frames,ignore_index=True);near=f[f['X (m)'].between(-.1,1.5)&f['Z (m)'].between(-.3,.35)].copy()
 speed2=sum(near['Velocity['+k+'] (m/s)']**2 for k in 'ijk');near['speed_m_s']=np.sqrt(speed2);near['p0_meanflow_Pa']=near['Pressure (Pa)']+500*speed2
 field=dict(active_cells=len(f),omega_floor_cells=int((f['Specific Dissipation Rate (/s)']<=1.0001e-10).sum()),k_floor_cells=int((f['Turbulent Kinetic Energy (J/kg)']<=1.0001e-10).sum()),viscosity_ratio_cap_cells=int((f['Turbulent Viscosity Ratio']>=99999).sum()),max_viscosity_ratio=float(f['Turbulent Viscosity Ratio'].max()),speed_max_near_m_s=float(near.speed_m_s.max()),meanflow_p0_max_near_Pa=float(near.p0_meanflow_Pa.max()),meanflow_p0_p99_near_Pa=float(near.p0_meanflow_Pa.quantile(.99)),pabs_min_Pa=float(f['Absolute Pressure (Pa)'].min()))
 field['max_speed_location']=near.loc[near.speed_m_s.idxmax(),['region','X (m)','Z (m)','Pressure (Pa)','Specific Dissipation Rate (/s)','speed_m_s','p0_meanflow_Pa']].to_dict()
 field['max_head_location']=near.loc[near.p0_meanflow_Pa.idxmax(),['region','X (m)','Z (m)','Pressure (Pa)','Wall Distance (m)','Turbulent Kinetic Energy (J/kg)','Specific Dissipation Rate (/s)','Turbulent Viscosity Ratio','Volume (m^3)','Cell Quality','speed_m_s','p0_meanflow_Pa']].to_dict()
 field['head_gt1p1q_near_cells']=int((near.p0_meanflow_Pa>178200).sum())
 field['head_gt1p1q_near_volume_fraction']=float(near.loc[near.p0_meanflow_Pa>178200,'Volume (m^3)'].sum()/near['Volume (m^3)'].sum())
 o['field_exports'][label]=field
o['energy_screen_caution']='Mean-flow piezometric total pressure is a consistency diagnostic, not a strict universal Bernoulli bound in unsteady viscous RANS.'
(run/'work_review.json').write_text(json.dumps(o,indent=2),encoding='utf8')
(h/'validation'/('review_'+run.name+'.json')).write_text(json.dumps(o,indent=2),encoding='utf8')
brief={k:v for k,v in o.items() if k not in ['window_results','field_exports']}
brief['last_windows']=o['window_results'][-3:]
brief['field_exports']=o['field_exports']
print(json.dumps(brief,indent=2))
