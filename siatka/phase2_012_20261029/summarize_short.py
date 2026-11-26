import json,csv,hashlib
from pathlib import Path
p=Path(r"F:\ntnu\mesh_screening_20261028\flow012_short_20261029")
summary={}
for name in ["H0_0ms","F18_18ms"]:
 d=p/name
 with (d/"history.csv").open() as f:rs=[{k:float(v) if v else None for k,v in r.items()} for r in csv.DictReader(f)]
 setup=json.loads((d/"setup.json").read_text());done=json.loads((d/"completed.json").read_text());last=rs[-1]
 summary[name]={"setup":setup,"completed":done,"last":last,"peak_CFL":max(r["max_convective_CFL"] for r in rs),"peak_velocity_m_s":max(r["max_velocity_m_s"] for r in rs),"seconds_per_step":last["wall_seconds"]/len(rs),"checkpoint_bytes":(d/"checkpoint.sim").stat().st_size,"history_rows":len(rs)}
 if name=="F18_18ms":
  summary[name]["startup_extrapolation_hours_per_root_c_over_U"]=(1.19/18)/last["physical_time_s"]*last["wall_seconds"]/3600
  summary[name]["coefficient_arithmetic_verified"]=abs(last["CD"]-last["Fx_half_N"]/(.5*setup["rho_kg_m3"]*18**2*setup["S_ref_half_m2"]))<1e-12
identity=json.loads((p/"source_identity.json").read_text());summary["original_mesh_unchanged"]=hashlib.sha256(Path(identity["original"]).read_bytes()).hexdigest()==identity["sha256"]
summary["run_exit"]=json.loads((p/"run_exit.json").read_text())
(p/"final_summary.json").write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
