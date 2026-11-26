from pathlib import Path
import json
import numpy as np,pandas as pd
h=Path(__file__).resolve().parents[1];r=h/'cases/SP_C_split0_overset/c0_forewall36_20261103_022619'
o={}
for n in ['main','flap']:
 sets={}
 for label in ['source','partitioned','after']:
  p=r/(n+'_'+label+'_native_wall_vertices.csv')
  a=pd.read_csv(p);pts=np.unique(np.round(a[['X (m)','Z (m)']].to_numpy(),12),axis=0);sets[label]=set(map(tuple,pts))
 q={}
 for label in ['partitioned','after']:
  missing=sorted(sets['source']-sets[label]);added=sorted(sets[label]-sets['source'])
  q[label]=dict(source_unique=len(sets['source']),after_unique=len(sets[label]),missing_count=len(missing),added_count=len(added),missing_bounds=np.array(missing).T.tolist() if len(missing)<12 else np.column_stack((np.min(missing,axis=0),np.max(missing,axis=0))).tolist(),missing_sample=missing[:12],added_sample=added[:12])
 o[n]=q
(r/'work_native_vertex_delta.json').write_text(json.dumps(o,indent=2),encoding='utf8');print(json.dumps(o,indent=2))
