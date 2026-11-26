from pathlib import Path
import pandas as pd,json
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_distance_20261102_232050';out={}
for tag in ['control_source','step_25']:
 out[tag]={}
 for region in ['Background','FlapOverset']:
  d=pd.read_csv(run/(region+'_'+tag+'_volume.csv'));d=d[d['Overset Cell Status']==0]
  floor=d[d['Specific Dissipation Rate (/s)']<=1.0001e-10];kf=d[d['Turbulent Kinetic Energy (J/kg)']<=1.0001e-10]
  out[tag][region]=dict(omega_count=len(floor),k_count=len(kf),omega_floor_wall_distance_quantiles={str(q):float(floor['Wall Distance (m)'].quantile(q)) if len(floor) else None for q in [0,.5,1]},omega_floor_x_range=[float(floor['X (m)'].min()),float(floor['X (m)'].max())] if len(floor) else [],omega_floor_cell_quality_min=float(floor['Cell Quality'].min()) if len(floor) else None)
(h/'validation/C0_floor_localization_step25.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
