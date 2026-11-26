from pathlib import Path
import json,pandas as pd,numpy as np
h=Path(__file__).resolve().parents[1]
b=pd.read_csv(h/'cases/SP_B_split0_fixed/steady_init_20261102_195203/stabilize_20261102_195203/foil_pressure.csv')
root=h/'audit/comparison_SP_C_20261102_222216';out={}
for body in ['main','flap']:
 c=pd.read_csv(root/(body+'_wall.csv'));cs=c[['X (m)','Z (m)']].to_numpy();bs=b[['X (m)','Z (m)']].to_numpy();dist=np.linalg.norm(cs[:,None,:]-bs[None,:,:],axis=2);idx=dist.argmin(axis=1);bs=bs[idx];delta=cs-bs
 x=bs-bs.mean(0);y=cs-cs.mean(0);u,_,vt=np.linalg.svd(x.T@y);r=u@vt;pred=x@r+cs.mean(0)
 out[body]=dict(points=len(cs),delta_mean=delta.mean(0).tolist(),delta_min=delta.min(0).tolist(),delta_max=delta.max(0).tolist(),distance_quantiles=np.quantile(np.linalg.norm(delta,axis=1),[0,.25,.5,.9,.99,1]).tolist(),rigid_rotation_deg=float(np.degrees(np.arctan2(r[0,1],r[0,0]))),rigid_fit_rms_m=float(np.sqrt(np.mean((cs-pred)**2))),before_rms_m=float(np.sqrt(np.mean(delta**2))),B_min=bs.min(0).tolist(),B_max=bs.max(0).tolist(),C_min=cs.min(0).tolist(),C_max=cs.max(0).tolist())
print(json.dumps(out,indent=2));(h/'validation/BC_wall_pose_diagnosis.json').write_text(json.dumps(out,indent=2),encoding='utf8')
