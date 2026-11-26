"""Generate immutable wave-only DOE specifications; no STAR processes are launched."""
import json,csv,shutil,math
from pathlib import Path
root=Path(r'F:\ntnu\wave_depth_20261029')
source=Path(r'F:\ntnu\mesh_screening_20261028\inspection\baseline_clean.sim')
rows=[]
for lam in (20,30):
 for depth in (12,16,24):
  rows.append(dict(id=f'W{lam}_H{depth}_X3',lambda_m=lam,depth_m=depth,height_m=.5,dt_s=.002,domain_lambda=3,mesh=True))
 rows.append(dict(id=f'W{lam}_H16_X4',lambda_m=lam,depth_m=16,height_m=.5,dt_s=.002,domain_lambda=4,mesh=True))
for dt,tag in ((.001,'DT1ms'),(.004,'DT4ms')):
 rows.append(dict(id=f'W20_H16_X3_{tag}',lambda_m=20,depth_m=16,height_m=.5,dt_s=dt,domain_lambda=3,mesh=True))
manifest=[]
for item in rows:
 name=item['id'];folder=root/name;folder.mkdir(exist_ok=True)
 job=folder/'job.json';base=folder/'baseline_copy.sim'
 if not job.exists():job.write_text(json.dumps(item,indent=2),encoding='utf-8')
 if not base.exists():shutil.copy2(source,base)
 L=item['lambda_m'];h=item['depth_m'];N=item['domain_lambda'];k=2*math.pi/L;c=math.sqrt(9.81/k*math.tanh(k*h))
 d=dict(**item,phase_speed_mps=c,intrinsic_period_s=L/c,encounter_period_s=L/(18+c),kh=k*h,
  estimated_CFL_x=18*item['dt_s']/.2048,estimated_n_steps_per_encounter_period=(L/(18+c))/item['dt_s'],
  x_min_m=-(N/2-.25)*L,x_max_m=(N/2+.25)*L,bottom_z_m=2-h,top_z_m=12,
  x_mesh_m=.2048,z_mesh_m=.0256,source_sim=str(base),expected_sim=str(folder/'built.sim'))
 manifest.append(d)
(root/'cases.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with (root/'cases.csv').open('w',newline='',encoding='utf-8') as fp:
 w=csv.DictWriter(fp,fieldnames=list(manifest[0].keys()));w.writeheader();w.writerows(manifest)
print("CREATED",len(manifest),"cases; baseline copies=",sum(int((root/r['id']/'baseline_copy.sim').exists()) for r in rows))
