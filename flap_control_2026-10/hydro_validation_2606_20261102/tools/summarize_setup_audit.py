from pathlib import Path
import json,re,pandas as pd
h=Path(__file__).resolve().parents[1];out={}
for k,folder in [('B','comparison_SP_B_20261102_234628'),('C_distance','comparison_SP_C_20261102_234320')]:
 p=h/'audit'/folder;assert json.loads((p/'status.json').read_text())['status']=='inspection_complete'
 s=(p/'native_setup.txt').read_text();row=dict(source=str(p),frozen_solver_lines=[x for x in s.splitlines() if 'frozen=' in x],models=re.findall(r'^model=(.+)$',s,re.M),region_motion=re.findall(r'^region=(.+)$',s,re.M),grid_velocity=re.findall(r'^Grid.+$',s,re.M),unread_properties=[x for x in s.splitlines() if 'UNREAD_' in x],wall_status={})
 for group in ['main','flap']:
  d=pd.read_csv(p/(group+'_wall_status.csv'));a=dict(rows=len(d))
  for fld in ['Overset Cell Status','Overset Error Status']:
   if fld in d:a[fld]={str(v):int(n) for v,n in d[fld].value_counts(dropna=False).items()}
  row['wall_status'][group]=a
 out[k]=row
out['models_only_C']=sorted(set(out['C_distance']['models'])-set(out['B']['models']))
out['models_only_B']=sorted(set(out['B']['models'])-set(out['C_distance']['models']))
out['scientific_approved']=False
(h/'validation/BC_native_setup_comparison.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
