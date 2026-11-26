"""Resume the authorized sealed Stokes-V phase-identification cases."""
import math
import os
from pathlib import Path
import shutil
import time

from resume import c, D, P, CPUS, job, run_day

DT=.0005
INNER=12
CFL_LIMIT=.90

STATE = D/"WAVE_PHASE_MAP_STATUS.json"
MACRO = D/"phase_identification_macro/MiniVofStokes.java"
READBACK = D/"NIGHT_WAVE_FINAL_READBACK.json"
PAUSE = D/"PAUSED_FOR_MEETING_20261106.json"
MEETING_STOP = "User requested safe pause for meeting, 2026-11-06."
RESUME_STOP = D/"MEETING_PAUSE_STOP_20261106_ARCHIVED.txt"
FIXED_STAGE = "PHASE_MAP_WAVE_FIXED"
CYCLES = 3
ORIGIN = 1.506
PERIOD = .455553045796036
START_GATE = ORIGIN+1.05
FIXED_STEPS = math.ceil((START_GATE+CYCLES*PERIOD-1.806)/DT)
STATE_DATA = {"dt_s": DT, "inner": INNER, "interface_CFL_limit": CFL_LIMIT, "period_s": PERIOD, "height_m": .10,
              "fixed_gate_starts_s": START_GATE, "accepted_cycles_required": CYCLES,
              "active_amplitude_deg": 1, "segments": [], "training_approved": False}

def status(**updates):
    STATE_DATA.update(updates)
    c.coex.save(STATE, STATE_DATA)

def job_path(stage, source):
    path=Path(c.read(P/"DAY_STATUS.json")["output"])
    if not path.name.startswith(stage+"_") or path.parent!=P/"runs":
        raise RuntimeError("Unexpected STAR run folder")
    if c.read(path/"job.json")["input_sha256"]!=c.sha(source):
        raise RuntimeError("Run provenance does not match its input")
    return path

def recover(folder, origin, steps):
    row=c.read(folder/"LATEST_CHECKPOINT.json")
    path=Path(row["path"])
    n=int(row["step_in_job"])
    t=float(row["time_s"])
    if (path.parent!=folder or path.suffix.lower()!=".sim" or not row["complete_write"]
            or path.stat().st_size!=row["bytes"] or not 0<n<=steps
            or abs(t-(origin+n*DT))>1e-8):
        raise RuntimeError("No complete advancing checkpoint")
    rows=[r for r in c.tail(folder/"history.csv") if float(r["time_s"])<=t+1e-9]
    if (len(rows)!=n or abs(float(rows[-1]["time_s"])-t)>1e-8
            or float(rows[-1]["interface_CFL"])>CFL_LIMIT
            or float(rows[-1]["max_CFL"])>25):
        raise RuntimeError("Checkpoint and history or safety check mismatch")
    residuals=c.tail(folder/"residual_per_step.csv")
    tail=[r for r in residuals if t-4.5*DT<=float(r["time_s"])<=t+1e-9]
    if (len(tail)!=35 or any(r["normalized"].lower()!="true" or
                            not math.isfinite(float(r["last"])) or abs(float(r["last"]))>.01 for r in tail)):
        raise RuntimeError("Saved checkpoint lacks verified residual coverage")
    history=Path(c.read(folder/"AF_RESUME_HISTORY.json")["path"])
    if history.parent!=folder or history.stat().st_size<=0:
        raise RuntimeError("Missing local AF history")
    return path,t,history,n

def integrate(stage, source, t, history, steps, *, moving=False, options=None):
    done=0
    faults=0
    while done<steps:
        if c.STOP.exists() or shutil.disk_usage(P).free < 9*2**30:
            raise RuntimeError("STOP or less than 9 GiB free")
        n=steps-done
        status(operation="STARTING_"+stage, solver_start_s=t, source=str(source), requested_steps=n)
        config=dict(calm_only=False, clean_calm=False, moving=moving, amplitude=.05,
                    old_amplitude=0, ramp_s=.456, ramp_origin_s=ORIGIN,
                    dt=DT, inner=INNER, phase_interface_cfl_max=CFL_LIMIT,
                    source_af_history=history.as_posix(), af_branch_history=False,
                    save_interval_s=.05, early_save_interval_s=.01, early_save_steps=200, steps=n, limit_seconds=min(15*3600,600+7*n))
        config.update(options or {})
        try:
            result=job(stage,source,t,macro_source=MACRO,**config)
        except (RuntimeError,OSError) as error:
            if c.STOP.exists():
                raise
            run_day.protected_idle()
            folder=job_path(stage,source)
            log=folder/"client.log"
            with log.open("rb") as stream:
                stream.seek(max(0,log.stat().st_size-20000))
                tail=stream.read()
            if b"Connection reset" not in tail or (folder/"SOLVE_STATUS.json").exists():
                raise
            checkpoint,t1,hist,n1=recover(folder,t,n)
            faults=faults+1 if n1<500 else 0
            STATE_DATA["segments"].append(dict(stage=stage,folder=str(folder),end_s=t1,
                 status="RECOVERED_TRANSPORT",checkpoint=str(checkpoint),sha256=c.sha(checkpoint)))
            status(operation="TRANSPORT_RECOVERED", last_error=str(error))
            if faults>=3 or (moving and not config.get("resume_active_allowed")):
                raise RuntimeError("Repeated short transport losses or moving restart not qualified")
        else:
            if (result["status"]!="NUMERICAL_END_PASS" or not result["transport_ok"]
                    or result["samples"]!=n or not result["state"]["residual_pass"]):
                status(last_result=result)
                raise RuntimeError(f"{stage} {result['status']} after {result['samples']} steps")
            folder=Path(result["checkpoint"]).parent
            checkpoint,t1,hist,n1=recover(folder,t,n)
            if c.sha(checkpoint)!=result["checkpoint_sha256"] or n1!=n:
                raise RuntimeError("Completed checkpoint integrity or step count mismatch")
            STATE_DATA["segments"].append(dict(stage=stage,folder=str(folder),end_s=t1,
                 status="COMPLETE",checkpoint=str(checkpoint),sha256=result["checkpoint_sha256"]))
        source,t,history=checkpoint,t1,hist
        done+=n1
        status(last_checkpoint=str(source),physical_time_s=t,steps_completed=done)
    return source,t,history

def paused_source():
    proof=c.read(PAUSE)
    source=Path(proof["source"])
    backup=Path(proof["checkpoint"])
    t=float(proof["physical_time_s"])
    digest=proof["files"][backup.name]["sha256"]
    if (proof["status"]!="PAUSED_USER_CHECKPOINT_VERIFIED" or abs(t-1.956)>1e-9
            or (proof["dt_s"],proof["inner"],proof["interface_cfl_limit"])!=(DT,INNER,CFL_LIMIT)
            or abs(proof["ramp_origin_s"]-ORIGIN)>1e-9 or proof["flap_deg"]!=0
            or not proof["residual_pass"] or c.sha(source)!=digest or c.sha(backup)!=digest):
        raise RuntimeError("Meeting checkpoint or parameters failed verification")
    path,time_saved,history,n=recover(source.parent,t-proof["steps_completed"]*DT,proof["steps_completed"])
    if (path!=source or history!=Path(proof["source_history"]) or abs(time_saved-t)>1e-9
            or n!=proof["steps_completed"] or c.STOP.read_text()!=MEETING_STOP or RESUME_STOP.exists()):
        raise RuntimeError("Pause marker, history or checkpoint lineage changed")
    STATE_DATA["segments"].append(dict(stage=FIXED_STAGE,folder=str(source.parent),end_s=t,
                                      status="PAUSED_VERIFIED",checkpoint=str(source),sha256=digest))
    return source,t,history,n

def wait_for_idle():
    until=time.monotonic()+8*3600
    while time.monotonic()<until:
        if not c.STOP.is_file() or c.STOP.read_text()!=MEETING_STOP or RESUME_STOP.exists():
            raise RuntimeError("Meeting stop marker changed during deferred resume")
        if c.LOCK.exists():
            raise RuntimeError("Another Mini controller has acquired the lock")
        try:
            run_day.protected_idle()
            return
        except RuntimeError as error:
            if not str(error).startswith(("Other STAR/MPI present:", "Independent CFD queue has priority:", "Dedicated port is occupied")):
                raise
            status(operation="WAITING_FOR_RESOURCES",reason=str(error))
        time.sleep(30)
    raise RuntimeError("STAR resources remained occupied for 8 hours")

def main():
    resume_pause="--resume-meeting" in sys.argv
    if resume_pause:
        source,t,history,prior_steps=paused_source()
        status(operation="CHECKING_RESOURCES",physical_time_s=t,last_checkpoint=str(source))
        wait_for_idle()
    else:
        run_day.protected_idle()
        if c.STOP.exists():
            raise RuntimeError("Existing STOP marker")
        proof=c.read(READBACK)
        source=Path(proof["source"])
        t=float(proof["evidence"]["time_s"])
        if proof["status"]!="VERIFIED" or abs(t-1.806)>1e-9 or c.sha(source)!=proof["sha256"]:
            raise RuntimeError("Initial 1.806 s checkpoint failed verification")
        history=Path(c.read(source.parent/"AF_RESUME_HISTORY.json")["path"])
        if not history.is_file():
            raise RuntimeError("Missing initial AF history")
        prior_steps=0
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        if resume_pause:
            run_day.protected_idle()
            if c.STOP.read_text()!=MEETING_STOP or RESUME_STOP.exists():
                raise RuntimeError("Meeting pause marker changed before launch")
            c.STOP.rename(RESUME_STOP)
        c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in CPUS)
        status(operation="RESUMING_WAVE_FIXED" if resume_pause else "STARTING_WAVE_FIXED",reason=None)
        source,t,history=integrate(FIXED_STAGE,source,t,history,FIXED_STEPS-prior_steps)
        from wave_phase_map_analysis import finish_fixed_and_run_active
        finish_fixed_and_run_active(source,t,history)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()

if __name__=="__main__":
    # Use one module instance when importing the analysis after the fixed run.
    import sys
    sys.modules["wave_phase_map_campaign"]=sys.modules[__name__]
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        status(operation="HOLD",reason=str(error))
        raise
