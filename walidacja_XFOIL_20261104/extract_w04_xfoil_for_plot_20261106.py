# Read-only extraction of W04 URANS data and XFOIL polars for off-line plotting.
# Does not launch/modify STAR-CCM+ or the CFD queue.
from pathlib import Path
import csv, json, zipfile, hashlib
src=Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W04_20261103_182412_f27930")
xp=Path(r"F:\ntnu\XFOIL_validation_20261104\AbbottStyle_Re20M_20261106")
out=Path(r"F:\ntnu\XFOIL_validation_20261104\W04_comparison_20261106")
out.mkdir(parents=True,exist_ok=True)
TMIN,TMAX=13.0,19.28
def readcsv(files, cols, key):
    data={}
    for file in files:
        with (src/file).open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                t=float(r["time_s"])
                if not TMIN<=t<=TMAX:continue
                if "x_m" in r and float(r["x_m"]) not in (0.0,-0.5):continue
                k=(t, float(r["x_m"])) if "x_m" in r else t
                data[k]={c:r[c] for c in cols}
    keys=sorted(data)
    return keys,data
hkeys,h=readcsv(("prior_history.csv","history.csv"),("time_s","CL_hydrodynamic","CD_total","Fx_N","Fz_N"),"time_s")
gkeys,g=readcsv(("prior_gauges.csv","gauges.csv"),("time_s","x_m","eta_actual_m"),"time_s")
with (out/"W04_CFD_forces_13to19s.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f);w.writerow(["time_s","CL_hydrodynamic","CD_total","Fx_N","Fz_N"])
    for t in hkeys:
        r=h[t];w.writerow([r[x] for x in ("time_s","CL_hydrodynamic","CD_total","Fx_N","Fz_N")])
with (out/"W04_gauges_x0_minus0p5_13to19s.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.writer(f);w.writerow(["time_s","x_m","eta_actual_m"])
    for t,x in gkeys:
        r=g[t,x];w.writerow([r[c] for c in ("time_s","x_m","eta_actual_m")])
review=json.loads((src/"independent_cycle_review.json").read_text(encoding="utf-8"))
print("W04",review["H"],review["L"],review["status"],review["scientific_NWAR_accepted"])
print("CYCLES",[(c["number"],round(c["start"],5),round(c["end"],5),bool(c["analysis_included"])) for c in review["cycles"]["cycles"]])
print("HISTORY",len(hkeys),min(hkeys),max(hkeys))
print("GAUGES",len(gkeys))
for file in ("independent_cycle_review.json","wave_setup_audit.json","request.json"):
    (out/file).write_bytes((src/file).read_bytes())
for file in ("polar_positive.txt","polar_negative.txt","foil_66_012_a08mod_f025.dat"):
    (out/file).write_bytes((xp/file).read_bytes())
manifest={"source_dir":str(src),"source_run_id":review["id"],
          "analysis_accepted":review["scientific_NWAR_accepted"],
          "cfd_coefficient_denominator_N":review["force_reference"]["coefficient_denominator_N"],
          "reference_CL":review["force_reference"]["CL"],"reference_CD":review["force_reference"]["CD"],
          "XFOIL":{"Re":20000000,"Ma":0.0,"panels":240,"Ncrit":9,"Xtr_top_bottom":0.01},
          "data_window_s":[TMIN,TMAX],"wave":{"H_m":review["H"],"lambda_m":review["L"]},
          "review_cycles":review["cycles"]["analyzed_cycle_numbers"]}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
zip_path=out.parent/"W04_XFOIL_phase_comparison_sources_20261106.zip"
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for p in out.iterdir():
        if p.is_file():z.write(p,arcname=p.name)
copy=Path(r"G:\My Drive\ChatGPT")/zip_path.name
copy.write_bytes(zip_path.read_bytes())
print("ZIP",zip_path.stat().st_size,copy)
