from pathlib import Path
import json,pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1]
b=pd.read_csv(h/'cases/SP_B_split0_fixed/steady_init_20261102_195203/stabilize_20261102_195203/foil_pressure.csv')
root=h/'audit/comparison_SP_C_20261102_222216'
c=pd.concat([pd.read_csv(root/'main_wall.csv').assign(body='main'),pd.read_csv(root/'flap_wall.csv').assign(body='flap')],ignore_index=True)
coords=['X (m)','Y (m)','Z (m)']
bp=b[coords].to_numpy();cp=c[coords].to_numpy()
dist=np.linalg.norm(bp[:,None,:]-cp[None,:,:],axis=2);nearest=dist.argmin(axis=1);d=dist[np.arange(len(b)),nearest]
report=dict(B_samples=len(b),C_samples=len(c),max_nearest_wall_centroid_distance_m=float(d.max()),unique_matches=len(set(nearest.tolist())),same_wall_centroid_set_to_1nm=bool(d.max()<1e-9 and len(set(nearest.tolist()))==len(c)),interpretation='Identical face centroid locations would exclude a hidden foil pose change; volume mesh and near-wall connectivity still differ.')
for body in ['main','flap']:
 mask=c.iloc[nearest].body.to_numpy()==body
 report[body]=dict(mean_delta_p_Pa=float((c.iloc[nearest]['Pressure (Pa)'].to_numpy()-b['Pressure (Pa)'].to_numpy())[mask].mean()),max_abs_delta_p_Pa=float(np.abs(c.iloc[nearest]['Pressure (Pa)'].to_numpy()-b['Pressure (Pa)'].to_numpy())[mask].max()))
(h/'validation/BC_wall_coordinate_identity.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
