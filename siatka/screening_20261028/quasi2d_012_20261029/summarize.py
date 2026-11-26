import sys,json,csv,math,datetime
from pathlib import Path
r=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029")
def read(p,d=None):
 try:return json.loads(p.read_text(encoding="utf-8-sig"))
 except (OSError,ValueError):return d
runs=[]
for d in sorted(r.glob("M*")):
 if not d.is_dir():continue
 m=read(d/"measurement.json");timing=read(d/"mesh_timing.json")
 if m and timing:m["metrics"].update(timing);(d/"measurement.json").write_text(json.dumps(m,indent=2))
 for h in sorted(d.glob("*/history.csv")):
  try:
   with h.open() as f:rows=[{k:float(v) if v else None for k,v in x.items()} for x in csv.DictReader(f) if None not in x]
  except (ValueError,OSError):continue
  if not rows:continue
  last=rows[-1];u=read(h.parent/"setup.json",{}).get("speed_m_s",0);done=read(h.parent/"completed.json")
  wall=last["wall_seconds"];t=last["physical_time_s"]
  runs.append({"mesh":d.name,"run":h.parent.name,"completed":bool(done),"steps":len(rows),"last":last,"seconds_per_step":wall/len(rows),"seconds_per_physical_second":wall/t if t else None,"hours_per_c_over_U":wall/t*1.19/18/3600 if t and u else None,"speedup_vs_old_3d_physical_time":(300.699/.00015)/(wall/t) if t and u else None,"peak_velocity":max(x["max_velocity_m_s"] for x in rows),"peak_cfl":max(x["max_convective_CFL"] for x in rows)})
comparisons=[]
for a in runs:
 for b in runs:
  if a["mesh"]==b["mesh"] and a["run"]<b["run"] and a["last"].get("CD") and b["last"].get("CD") and abs(a["last"]["physical_time_s"]-b["last"]["physical_time_s"])<1e-9:
   comparisons.append({"a":a["mesh"]+"/"+a["run"],"b":b["mesh"]+"/"+b["run"],"time_s":a["last"]["physical_time_s"],"CD_difference_pct_of_a":100*(b["last"]["CD"]/a["last"]["CD"]-1),"CL_difference_pct_of_a":100*(b["last"]["CL_total"]/a["last"]["CL_total"]-1)})
result={"updated":datetime.datetime.now().astimezone().isoformat(),"purpose":"Startup diagnostics and measured throughput, not converged NWAR results","runs":runs,"matched_time_comparisons":comparisons}
(r/"campaign_summary.json").write_text(json.dumps(result,indent=2))
for x in runs:print(x["mesh"],x["run"],"n",x["steps"],"t",round(x["last"]["physical_time_s"],6),"s/step",round(x["seconds_per_step"],3),"CD",x["last"]["CD"],"CL",x["last"]["CL_total"])
print(json.dumps(comparisons,indent=2))
