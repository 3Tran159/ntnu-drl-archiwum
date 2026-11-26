import csv,json,math,hashlib,datetime
from pathlib import Path
R=Path("F:/ntnu/mesh_screening_20261028/force_stabilization_20261029")
P=Path("E:/ntnu/quasi2d_waves_20261029/W20_H24_X4_GPUprop_environmentalOutlet_pressureTol01_dt1ms_r14")
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats(rows):
 def vals(k):return [r[k] for r in rows]
 w=vals("Mass Imbalance of water (kg/s)");a=vals("Mass Imbalance of air (kg/s)")
 return {"cells":len(rows),"water_net_kg_s":math.fsum(w),"water_absolute_kg_s":math.fsum(abs(v) for v in w),"water_positive_kg_s":math.fsum(v for v in w if v>0),"water_negative_kg_s":math.fsum(v for v in w if v<0),"air_net_kg_s":math.fsum(a),"air_absolute_kg_s":math.fsum(abs(v) for v in a),"net_volume_equivalent_m3_s":math.fsum(x/1000+y/1.2 for x,y in zip(w,a))}
out={"created_at":datetime.datetime.now().astimezone().isoformat(),"title":"Calibrated spatial distribution of phase mass imbalance in the pressure-accuracy probe","case":str(P),"method":"Sum unsmoothed cell-centred kg/s directly; no cell-volume multiplication.","gate_pct_inlet":0.01,"diagnostic_only":True,"snapshots":[]}
for tag in ("0.612","0.617","0.618","0.625"):
 p=P/("local_balance_t"+tag+".csv");j=P/("local_balance_t"+tag+".json")
 native=json.loads(j.read_text())
 with p.open(newline="") as f: rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 totals=stats(rows)
 zones={"inlet_forcing": [r for r in rows if r["X (m)"] < -15],"unforced_core":[r for r in rows if -15 <= r["X (m)"] < 25],"outlet_damping":[r for r in rows if r["X (m)"] >=25]}
 phases={"air_alpha_le_1e-6":[r for r in rows if r["Volume Fraction of water"]<=1e-6],"interface_1e-6_to_1minus1e-6":[r for r in rows if 1e-6<r["Volume Fraction of water"]<1-1e-6],"water_alpha_ge_1minus1e-6":[r for r in rows if r["Volume Fraction of water"]>=1-1e-6]}
 snap={"time_s":float(tag),"csv_sha256":digest(p),"json_sha256":digest(j),"source_native":native,"total":totals,"csv_water_minus_native_kg_s":totals["water_net_kg_s"]-native["native_water_kg_s"],"csv_air_minus_native_kg_s":totals["air_net_kg_s"]-native["native_air_kg_s"],"by_zone":{k:stats(v) for k,v in zones.items()},"by_phase":{k:stats(v) for k,v in phases.items()},"top_absolute_water_cells":sorted(rows,key=lambda r:abs(r["Mass Imbalance of water (kg/s)"]),reverse=True)[:12],"by_2m_x_bin":{str(x):stats([r for r in rows if x<=r["X (m)"]<x+2]) for x in range(-35,45,2)}}
 out["snapshots"].append(snap)
(R/"professor_r14_local_balance_review_draft.json").write_text(json.dumps(out,indent=2))
for s in out["snapshots"]:
 print(json.dumps({k:s[k] for k in ["time_s","total","csv_water_minus_native_kg_s","csv_air_minus_native_kg_s","by_zone","by_phase","top_absolute_water_cells"]}))
