import json,csv,math,sys
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
folder=r/(sys.argv[1] if len(sys.argv)>1 else "M02")/(sys.argv[2] if len(sys.argv)>2 else "H0_0ms")
with (folder/"fluid_final_fields.csv").open() as f:
 rows=[{k:float(v) for k,v in x.items()} for x in csv.DictReader(f)]
valid=[x for x in rows if all(math.isfinite(v) and abs(v)<1e100 for v in x.values())]
if not valid:raise RuntimeError("No valid field data")
keys=list(valid[0]);vk=next(k for k in keys if "Magnitude" in k);yk=next(k for k in keys if "Velocity[j]" in k);vf=next((k for k in keys if "Fraction" in k),None)
regions={"all":valid,"deep_water":[x for x in valid if x["Z (m)"]<1.8],"interface_band":[x for x in valid if abs(x["Z (m)"]-2)<.2],"air":[x for x in valid if x["Z (m)"]>2.2],"foil_near":[x for x in valid if -.1<x["X (m)"]<1.3 and abs(x["Z (m)"])<.3]}
out={"total_rows":len(rows),"valid_rows":len(valid),"top_velocity_cells":sorted(valid,key=lambda x:x[vk],reverse=True)[:10],"regions":{k:{"cells":len(xs),"max_velocity":max((x[vk] for x in xs),default=None),"max_abs_spanwise_velocity":max((abs(x[yk]) for x in xs),default=None)} for k,xs in regions.items()}}
(folder/"field_summary.json").write_text(json.dumps(out,indent=2))
print(json.dumps({"regions":out["regions"],"top3":out["top_velocity_cells"][:3]},indent=2))
