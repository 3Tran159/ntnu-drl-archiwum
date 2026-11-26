import csv,json
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
for name in ["M01","M02","M03"]:
 with (r/name/"mesh_cells.csv").open() as f:rows=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
 q=next(k for k in rows[0] if "Quality" in k);out=sorted(rows,key=lambda x:x[q])[:10]
 (r/name/"lowest_quality_locations.json").write_text(json.dumps(out,indent=2))
 print(name,out[:2])
