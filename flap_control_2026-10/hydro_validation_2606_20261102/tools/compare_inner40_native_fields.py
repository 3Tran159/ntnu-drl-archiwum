from pathlib import Path
import pandas as pd,numpy as np,json
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_distance_20261102_231609'
out={}
for label,folder,suffix in [('B',h/'audit/comparison_SP_B_20261102_222923','_volume.csv'),('C15',h/'audit/comparison_SP_C_20261102_223230','_volume.csv'),('C40',run,'_control_source_volume.csv')]:
 frames=[]
 for region in ['Background','FlapOverset']:
  p=folder/(region+suffix)
  if not p.exists():continue
  d=pd.read_csv(p)
  if 'Overset Cell Status' in d:d=d[d['Overset Cell Status']==0].copy()
  d['region']=region;frames.append(d)
 d=pd.concat(frames,ignore_index=True);near=d[d['X (m)'].between(-.1,1.5)&d['Z (m)'].between(-.3,.35)].copy()
 sp2=sum(near['Velocity['+k+'] (m/s)']**2 for k in 'ijk');near['speed']=np.sqrt(sp2);near['p0']=near['Pressure (Pa)']+500*sp2
 out[label]=dict(active_cells=len(d),omega_floor_cells=int((d['Specific Dissipation Rate (/s)']<=1.0001e-10).sum()),k_floor_cells=int((d['Turbulent Kinetic Energy (J/kg)']<=1.0001e-10).sum()),mu_ratio_cap_cells=int((d['Turbulent Viscosity Ratio']>=99999).sum()),max_mu_ratio=float(d['Turbulent Viscosity Ratio'].max()),max_speed_near=float(near.speed.max()),max_meanflow_p0_near_Pa=float(near.p0.max()),p99_meanflow_p0_near_Pa=float(near.p0.quantile(.99)),minimum_pabs_Pa=float(d['Absolute Pressure (Pa)'].min()),max_speed_cell=near.loc[near.speed.idxmax(),['X (m)','Z (m)','region','Pressure (Pa)','speed','p0']].to_dict())
(h/'validation/C0_inner40_native_fields.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
