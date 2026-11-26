import csv,json
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
for mesh in ["M02","M03"]:
 p=r/mesh/"H0_0ms/fluid_final_fields.csv"
 with p.open() as f:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
 alpha=next(k for k in rows[0] if "Fraction" in k);vel=next(k for k in rows[0] if "Magnitude" in k)
 sels={"water_alpha_gt_0p99":[x for x in rows if x[alpha]>.99],"water_dominated_alpha_gt_0p5":[x for x in rows if x[alpha]>.5],"resolved_interface_0p01_0p99":[x for x in rows if .01<x[alpha]<.99],"almost_air_alpha_lt_0p01":[x for x in rows if x[alpha]<.01]}
 d={n:{"cells":len(xs),"max_velocity_m_s":max((x[vel] for x in xs),default=None),"max_location":max(xs,key=lambda x:x[vel]) if xs else None} for n,xs in sels.items()}
 (p.parent/"hydro_phase_diagnostic.json").write_text(json.dumps(d,indent=2))
 print(mesh,{n:x["max_velocity_m_s"] for n,x in d.items()})
