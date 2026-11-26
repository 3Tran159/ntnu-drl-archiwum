from pathlib import Path
import pandas as pd,json
h=Path(__file__).resolve().parents[1];p=h/'cases/SP_C_split0_overset/c0_overlap_audit_20261103_002030/FlapOverset_mesh_full_plane.csv'
d=pd.read_csv(p);f=d[d['Overset Interpolation Type'].between(4,6)]
print(f.to_json(orient='records',indent=2))
