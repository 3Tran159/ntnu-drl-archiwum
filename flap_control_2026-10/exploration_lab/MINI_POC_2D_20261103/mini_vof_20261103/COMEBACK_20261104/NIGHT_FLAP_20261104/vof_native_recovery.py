import datetime as dt
import csv
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

import night_flap as night
import calm_pair_ready as pair
import run_day

OUT, STATUS, STOP, LOCK, OWNER = night.OUT,night.STATUS,night.STOP,night.LOCK,night.OWNER
OLD_STAGE="CALM_VOF_FIXED_SEALED_DT020"
NEW_SEALED="CALM_VOF_FIXED_SEALED_DT020_WMI_RESUME"
NEW_GAP="CALM_VOF_FIXED_GAP_DT020"


def limited_query(code):
    result=subprocess.run(["powershell","-NoProfile","-Command",code],capture_output=True,
        text=True,check=True,timeout=60,creationflags=run_day.FLAG)
    value=json.loads(result.stdout.strip() or "[]")
    return value if isinstance(value,list) else [value]


def rescue_source(state):
    s=night.read(night.HERE.parent/"DAY_STATUS.json")
    if s["stage"]!=OLD_STAGE or "Win32_Process" not in s.get("error","") or "timed out" not in s["error"]:
        raise RuntimeError("Expected the sealed VOF Windows process inventory timeout")
    run=Path(s["output"])
    receipt=night.read(run/"LATEST_CHECKPOINT.json")
    native=night.read(run/"SOLVE_STATUS.json")
    cp=Path(receipt["path"])
    if (not receipt["complete_write"] or cp!=run/"FINAL.sim" or cp.stat().st_size!=receipt["bytes"]
        or native["status"]!="HOLD_STOP_OR_DEADLINE" or abs(native["time_s"]-receipt["time_s"])>1e-9):
        raise RuntimeError("Sealed native stop or checkpoint not verified")
    pids=",".join(str(s[k]) for k in ("server_pid","native_pid","client_pid"))
    if limited_query(f"ConvertTo-Json -InputObject @(Get-Process -Id {pids},12380 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) -Compress") or limited_query(OWNER):
        raise RuntimeError("Previous STAR or controller still active")
    if STOP.read_text().strip()!="Review owned STAR. No new launch." or LOCK.read_text().strip()!="12380":
        raise RuntimeError("Unexpected stop or controller lock owner")
    dest=OUT/(OLD_STAGE+"_WMI_INTERRUPTED")
    dest.mkdir(exist_ok=True)
    for name in ("FINAL.sim","LATEST_CHECKPOINT.json","SOLVE_STATUS.json","history.csv","gauges.csv",
                 "PRESSURE_BELOW_VAPOR.csv","residual_per_step.csv","client.log"):
        if (dest/name).exists():
            if night.sha(run/name)!=night.sha(dest/name):
                raise RuntimeError("Recovery archive differs from verified source")
        else:
            night.archive(run/name,dest/name)
    digest=night.sha(dest/"FINAL.sim")
    _,rows=night.history(dest/"history.csv")
    if abs(float(rows[-1]["time_s"])-native["time_s"])>1e-9:
        raise RuntimeError("Saved history does not agree with native time")
    marker=night.HERE/"WMI_TIMEOUT_STOP_AUTOMATIC_ARCHIVED.txt"
    old_lock=night.HERE/"WMI_TIMEOUT_CONTROLLER_STALE_ARCHIVED.lock"
    if marker.exists() or old_lock.exists():
        raise RuntimeError("Archived automatic stop or lock already exists")
    STOP.rename(marker)
    LOCK.rename(old_lock)
    night.archive(marker,dest/"STOP_AUTOMATIC_ARCHIVED.txt")
    night.archive(old_lock,dest/"CONTROLLER_STALE_ARCHIVED.lock")
    state["runs"][OLD_STAGE].update(archive=str(dest),saved_time_s=native["time_s"],checkpoint_sha256=digest)
    return dest/"FINAL.sim",native["time_s"],rows


def compare(state,prior_sealed):
    a=state["runs"].get(NEW_SEALED,{})
    b=state["runs"].get(NEW_GAP,{})
    if "archive" not in a or "archive" not in b:
        return
    _,a_rows=night.history(Path(a["archive"])/"history.csv")
    _,b_rows=night.history(Path(b["archive"])/"history.csv")
    a_rows=prior_sealed+a_rows
    first={round(float(r["time_s"])/pair.DSTEP):r for r in a_rows}
    second={round(float(r["time_s"])/pair.DSTEP):r for r in b_rows}
    keys=sorted(first.keys() & second.keys())
    if len(keys)<round(.05/pair.DSTEP):
        return
    window=keys[-round(.05/pair.DSTEP):]
    if len(window)!=window[-1]-window[0]+1:
        raise RuntimeError("Common physical-time samples are not contiguous")
    def metrics(rows):
        return {"CL_buoyancy_corrected":statistics.mean(float(rows[k]["CL"]) for k in window),
                "CL_total":statistics.mean(float(rows[k]["Fz"])/3855.6 for k in window),
                "CD":statistics.mean(float(rows[k]["CD"]) for k in window),
                "pABS_flap_min_Pa":min(float(rows[k]["pflap"]) for k in window)}
    stable=all(x.get("status")=="PASS_CALM_FORCE_STABILIZATION" and x.get("transport_ok") for x in (a,b))
    summary=dict(status="STABILIZED_BOTH" if stable else "EXPLORATORY_MATCHED_TIME_WINDOW",
                 begin_s=window[0]*pair.DSTEP,end_s=window[-1]*pair.DSTEP,dt_s=pair.DSTEP,
                 sealed=metrics(first),gap=metrics(second),training_approved=False)
    night.coex.save(OUT/"CALM_VOF_MATCHED_COMPARISON.json",summary)
    state["runs"]["CALM_VOF_PAIR_DT020_RECOVERY"]=summary
    state["runs"]["SURROGATE_PILOT_DT020_RECOVERY"]={"status":"HOLD","reason":"Paired baseline requires stable forces and a distinct pilot budget"}
    if not stable or min(summary["sealed"]["pABS_flap_min_Pa"],summary["gap"]["pABS_flap_min_Pa"])<=night.VP:
        return
    stage="SURROGATE_PILOT_DT020_RECOVERY"
    if not night.await_resources(state,stage):
        return
    state.update(status="RUNNING",active=stage)
    night.coex.save(STATUS,state)
    source=Path(a["archive"])/"FINAL.sim"
    if night.sha(source)!=a["checkpoint_sha256"]:
        raise RuntimeError("Pilot source checksum mismatch")
    result=pair.run(stage,dict(source=source,expected_time=a["state"]["time_s"],expected_cells=17462,
        steps=round(.2/pair.DSTEP),moving=True,flow_cycle=True,calm_active_pilot=True))
    state["runs"][stage]=result
    if "archive" in result:
        pair.pilot_data(result,night.read(pair.D/"PAIR.json")["sealed"])


if __name__=="__main__":
    state=night.read(STATUS)
    source,start,prefix=rescue_source(state)
    filter_names=" OR ".join(f"Name='{name}'" for name in
        ("starccm+.exe","starccm+w.exe","star-ccm+.exe","smpd.exe","mpiexec.exe","impi.exe"))
    read_processes="$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process -Filter \""+filter_names+"\" | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath) | ConvertTo-Json -Compress"
    run_day.READ=read_processes
    night.READ=read_processes
    run_day.query=limited_query
    night.query=limited_query
    pair.query=limited_query
    pair.DSTEP=.0002
    pair.COMMON["dt"]=.0002
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        state["process_inventory_recovery"]="Saved native state, filter by exact STAR process names, timeout 60 s"
        m=night.read(pair.D/"PAIR.json")["gap"]
        if night.sha(Path(m["path"]))!=m["sha256"]:
            raise RuntimeError("Gap VOF mesh hash mismatch")
        budget=max(0,min(9800,int((night.END-time.time()-450)/2)))
        variants=((NEW_SEALED,dict(source=source,expected_time=start,expected_cells=17462,
                    steps=5200,matched_calm_fixed=True)),
                  (NEW_GAP,dict(fresh=True,mesh_override=Path(m["path"]).as_posix(),
                    mesh_override_sha256=m["sha256"],expected_cells=m["cells"],steps=5200,matched_calm_fixed=True)))
        for stage,opts in variants:
            if not night.await_resources(state,stage):
                state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
                continue
            state.update(status="RUNNING",active=stage)
            night.coex.save(STATUS,state)
            try:
                state["runs"][stage]=pair.run(stage,opts,budget_seconds=budget)
            except Exception as exc:
                state["runs"][stage]={"status":"HOLD","reason":str(exc)}
            night.coex.save(STATUS,state)
        compare(state,prefix)
        state["status"]="STOPPED" if STOP.exists() else "REVIEW"
    except Exception as exc:
        state.update(status="HOLD",reason=str(exc))
        raise
    finally:
        state["active"]=None
        night.coex.save(STATUS,state)
        if not limited_query(OWNER):
            LOCK.unlink()


