from pathlib import Path
import pandas as pd,json
h=Path(__file__).resolve().parents[1];out={}
for folder in ['c0_overlap_audit_20261103_002030','c0_overlap_distance_audit_20261103_002542','c0_overlap_patch05mm_20261103_003057']:
 out[folder]={}
 for region in ['Background','FlapOverset']:
  p=h/'cases/SP_C_split0_overset'/folder/(region+'_mesh_full_plane.csv');d=pd.read_csv(p);f=d[d['Overset Interpolation Type'].between(4,6)]
  if len(f):out[folder][region]=json.loads(f.to_json(orient='records'))
(h/'validation/overlap_difficult_cell_locations.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
