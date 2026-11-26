"""Join the two native segments without altering either solver export."""
import csv
import json
from pathlib import Path
import shutil

from run_day import HERE,sha

first=json.loads((HERE/"ACTIVE_FIRST_2D_RESULT.json").read_text())["18"]["result"]
last=json.loads((HERE/"ACTIVE_FIRST_2D_RESUME_RESULT.json").read_text())["result"]
a,b=Path(first["checkpoint"]).parent,Path(last["checkpoint"]).parent
if sha(Path(first["checkpoint"]))!=first["checkpoint_sha256"] or sha(Path(last["checkpoint"]))!=last["checkpoint_sha256"]:
    raise RuntimeError("Active checkpoint SHA mismatch")
with (a/"single_phase.csv").open() as f:
    r=csv.DictReader(f); columns=r.fieldnames; rows=list(r)
with (b/"single_phase.csv").open() as f:
    r=csv.DictReader(f)
    if r.fieldnames!=columns:
        raise RuntimeError("Active history schema mismatch")
    rows+=list(r)
if any(abs(float(row["time_s"])-.001*i)>1e-8 for i,row in enumerate(rows,1)):
    raise RuntimeError("Non-contiguous physical time")
d=b/"COMBINED_CYCLE"
d.mkdir(exist_ok=False)
with (d/"single_phase.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
for src in [a/"vertices_0000.csv",*sorted(a.glob("vertices_step*.csv")),*sorted(b.glob("vertices_step*.csv"))]:
    shutil.copy2(src,d/src.name)
angles=[float(r["delta_measured_deg"]) for r in rows]
full=(len(rows)==200 and last["transport_ok"] and last["status"]=="PASS_DIAGNOSTIC_SMOKE"
      and abs(angles[49]+2)<1e-7 and abs(angles[149]-2)<1e-7 and abs(angles[-1])<1e-7)
meta=dict(status="PASS_EXPLORATORY_FULL_CYCLE" if full else "HOLD",
          steps=len(rows),U_m_s=18,dt_s=.001,time_s=float(rows[-1]["time_s"]),
          first_checkpoint=str(Path(first["checkpoint"])),final_checkpoint=str(Path(last["checkpoint"])),
          restarted_at_s=first["state"]["time_s"],training_approved=False)
(d/"SOLVE_STATUS.json").write_text(json.dumps(meta,indent=2))
print(d)

