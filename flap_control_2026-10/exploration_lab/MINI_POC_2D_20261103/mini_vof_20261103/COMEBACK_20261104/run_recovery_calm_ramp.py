"""Bounded calm-water recovery on the existing one-core STAR controller."""
import csv
import json
import os
from pathlib import Path
import re
import statistics

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, READ, independent_jobs, new_job, protected_idle, query, sha

STAGE = "RECOVERY_CALM_RAMP_DT100US"
BASE = HERE/"WALL_FUNCTIONS_AUDIT"/"RECOVERY_V2_TE_PARTIAL"
RESULT = HERE/"RECOVERY_CALM_RAMP_RESULT.json"

def protect_w06():
    if not independent_jobs():
        protected_idle()
        return None
    if independent_jobs()!=[("W06","running")]:
        raise RuntimeError("Independent CFD is not the verified running W06 job")
    coex.CASE = Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W06_20261104_100235_3b75bb")
    coex.W06_LAUNCHER = json.loads((coex.CASE/"process.json").read_text())["pid"]
    log=(coex.CASE/"star.log").read_text(encoding="utf8",errors="replace")
    ranks=set(re.findall(r"(?m)^Process rank 0\s+\S+\s+(\d+)\s*$",log))
    if len(ranks)!=1:
        raise RuntimeError("Cannot identify W06 solver rank")
    coex.RANK = int(ranks.pop())
    coex.EXPECTED={p["ProcessId"] for p in query(READ) if "21.02.007-R8" in (p.get("ExecutablePath") or "")}
    coex.BASELINE_FILE=HERE/"RECOVERY_RAMP_W06_BASELINE.json"
    coex.WATCH=HERE/"RECOVERY_RAMP_W06_WATCH.csv"
    watcher=coex.W06Protection()
    watcher.make_baseline()
    watcher.preflight()
    with coex.WATCH.open("x",encoding="ascii",newline="") as f:
        csv.writer(f).writerow(("time","phase","w06_step","w06_physical_s","w06_rolling_median_s","slowdown_fraction","mini_steps"))
    return watcher

def main():
    if STOP.exists() or RESULT.exists():
        raise RuntimeError("Previous STOP/result requires review")
    audit=json.loads((BASE/"RECOVERY_MESH_AUDIT.json").read_text())
    mesh=Path(audit["mesh"])
    if audit["status"]!="OFFLINE_MESH_MOTION_PASS" or sha(mesh)!=audit["mesh_sha256"]:
        raise RuntimeError("Recovery mesh audit or SHA mismatch")
    with LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    watcher=None
    try:
        watcher=protect_w06()
        fixed=new_job(STAGE,dict(stokes=True,calm_only=True,fresh=True,foil=True,amplitude=0,old_amplitude=0,
            expected_time=0,calm_speed_ramp_s=.05,steps=40,inner=20,dt=.0001,mesh_override=mesh.as_posix(),
            mesh_override_sha256=audit["mesh_sha256"],limit_seconds=720),protection=watcher)
        folder=Path(fixed["checkpoint"]).parent
        with (folder/"history.csv").open(encoding="utf8") as f:
            rows=list(csv.DictReader(f))
        summary={"result":fixed,"wall_s":None,"next":"HOLD","night_approved":False}
        if len(rows)>5:
            with (folder/"step_wall.csv").open(encoding="utf8") as f:
                wall=[float(r["step_wall_s"]) for r in csv.DictReader(f)][5:]
            summary["wall_s"]=statistics.median(wall)
        if fixed["samples"]==40 and fixed["transport_ok"] and fixed["status"] in ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW"):
            windows=(rows[-20:-10],rows[-10:])
            summary["window_force_means"]={name:[statistics.mean(float(r[name]) for r in w) for w in windows] for name in ("CL","CD","Mh_per_m")}
            summary["next"]="REVIEW_RAMP_ONLY_BELOW_TARGET_SPEED"
        if watcher:
            summary["W06"]=dict(baseline_s=watcher.baseline,peak_slowdown=watcher.peak,stop=watcher.stopped)
        coex.save(RESULT,summary)
    except Exception as err:
        coex.save(RESULT,dict(status="HOLD",error=str(err),W06_stop=watcher.stopped if watcher else None))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()


