from pathlib import Path
import csv
import json
import os
import sys
import time

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

original=json.loads((OUT/"RESULT.json").read_text())
record=original["BASELINE"]
source=Path(record["checkpoint"])
mesh=json.loads((OUT/"MESH_AUDIT.json").read_text())
report=OUT/"RESULT_DT0333MS.json"
if STOP.exists() or report.exists() or record["status"]!="GAP_BASELINE_READY" or sha(source)!=record["checkpoint_sha256"]:
    raise RuntimeError("Diagnostic time-step preflight blocked")
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
try:
    guard=protect_w06("ACTIVE_GAP25_MATCHED_OUTER_DT0333MS_"+time.strftime("%H%M%S"))
    coex.save(report,dict(status="RUNNING",stage="DT0333MS"))
    result=new_job("ACTIVE_GAP25_MATCHED_OUTER_DT0333MS",
        dict(stokes=True,source=source,seeded_single_phase=True,foil=True,moving=True,single_phase=True,
             coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],expected_time=0,
             amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.2/600,steps=600,
             limit_seconds=2100),protection=guard,macro_source=OUT/"MiniVofStokes.java")
    result["W06"]=dict(baseline_s=guard.baseline,peak_slowdown=guard.peak,stop=guard.stopped) if guard else None
    path=Path(result["checkpoint"]).parent/"single_phase.csv"
    with path.open() as f:
        rows=list(csv.DictReader(f))
    angles=[float(r["delta_measured_deg"]) for r in rows]
    result["full_cycle"]=(result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
        and len(angles)==600 and min(angles)<-1.99 and max(angles)>1.99 and abs(angles[-1])<.01)
    coex.save(report,dict(status="PASS_EXPLORATORY_FULL_CYCLE" if result["full_cycle"] else "HOLD",
                          DT0333MS=result))
except Exception as exc:
    coex.save(report,dict(status="HOLD",error=str(exc)))
    raise
finally:
    LOCK.unlink()

