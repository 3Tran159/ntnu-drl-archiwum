from pathlib import Path
import pandas as pd,numpy as np,json,datetime
h=Path(__file__).resolve().parents[1];run=h/'cases/SP_C_split0_overset/c0_tight_turbulence_second_20261103_034119';out=dict(at=datetime.datetime.now().astimezone().isoformat(),scientific_approved=False)
for group in ['main','flap']:
 a=pd.read_csv(h/'audit/comparison_SP_B_20261102_234628'/(group+'_wall.csv'));b=pd.read_csv(run/(group+'_final_wall.csv'))
 xy=['X (m)','Z (m)'];v=a[xy].to_numpy();w=b[xy].to_numpy();d=np.sqrt(((v[:,None,:]-w[None,:,:])**2).sum(axis=2));idx=d.argmin(axis=1);near=d[np.arange(len(a)),idx]
 result=dict(B_rows=len(a),C_rows=len(b),unique_nearest_C=len(set(idx)),nearest_distance_max_m=float(near.max()),nearest_distance_p99_m=float(np.quantile(near,.99)),nearest_distance_median_m=float(np.median(near)),under_1um=int((near<1e-6).sum()),under_10um=int((near<1e-5).sum()),under_100um=int((near<1e-4).sum()))
 result['largest_offsets']=[dict(B_x=float(v[k,0]),B_z=float(v[k,1]),C_x=float(w[idx[k],0]),C_z=float(w[idx[k],1]),distance_m=float(near[k])) for k in np.argsort(near)[-4:][::-1]]
 out[group]=result
(run/'wall_nearest_offset_review.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
