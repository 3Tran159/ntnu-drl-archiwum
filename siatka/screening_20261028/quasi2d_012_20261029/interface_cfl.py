import csv,json
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
for mesh in ["M01","M02","M03"]:
 p=r/mesh/"F18_dt500us/fluid_final_fields.csv"
 if not p.exists():continue
 with p.open() as f:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
 alpha=next(k for k in rows[0] if "Fraction" in k);cfl=next(k for k in rows[0] if "Courant" in k)
 inter=[x for x in rows if .01<x[alpha]<.99]
 result={"global_max_CFL":max(x[cfl] for x in rows),"interface_0p01_to_0p99_cells":len(inter),"interface_max_CFL":max((x[cfl] for x in inter),default=None),"note":"Global near-wall convective CFL and interface CFL are different diagnostics. VOF dynamic substeps target CFL=0.5, max 20, inherited settings."}
 (p.parent/"interface_cfl.json").write_text(json.dumps(result,indent=2))
 print(mesh,result)
