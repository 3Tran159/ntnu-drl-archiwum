from pathlib import Path
import pandas as pd,numpy as np,json
h=Path(__file__).resolve().parents[1]
out={}
for label,folder in [('B',h/'audit/comparison_SP_B_20261102_222923'),('C',h/'audit/comparison_SP_C_20261102_223230')]:
 frames=[]
 for p in folder.glob('*_volume.csv'):
  df=pd.read_csv(p)
  if 'Overset Cell Status' in df:df=df[df['Overset Cell Status']==0].copy()
  df['region']=p.stem;frames.append(df)
 d=pd.concat(frames,ignore_index=True);d['speed_m_s']=np.sqrt(sum(d['Velocity['+k+'] (m/s)']**2 for k in 'ijk'))
 d['meanflow_piezometric_total_pressure_Pa']=d['Pressure (Pa)']+500*d.speed_m_s**2
 near=d[d['X (m)'].between(-.1,1.5)&d['Z (m)'].between(-.3,.35)]
 out[label]=dict(max_speed_row=near.loc[near.speed_m_s.idxmax()].to_dict(),total_pressure_max_row=near.loc[near.meanflow_piezometric_total_pressure_Pa.idxmax()].to_dict(),inlet_dynamic_pressure_Pa=162000,nearfield_total_pressure_quantiles={str(q):float(near.meanflow_piezometric_total_pressure_Pa.quantile(q)) for q in [.01,.5,.99,1]},caution='Mean-flow energy consistency screen only; local total pressure in viscous/unsteady RANS is not a strict universal bound or proof of the numerical cause.')
(h/'validation/BC_head_consistency_screen.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
