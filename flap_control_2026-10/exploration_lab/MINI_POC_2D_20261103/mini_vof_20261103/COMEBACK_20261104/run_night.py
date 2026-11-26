"""Night runner. The readiness and user approval documents are required inputs."""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import time

from run_day import HERE, ROOT, LOCK, STOP, protected_idle, new_job, sha
from export_trajectory import csv_rows, export

sys.path.insert(0,str(ROOT))
from night_review import T, W, K, harmonic, wave_review
import numpy as np

PARAMETERS={"U_m_s":18,"lambda_m":10,"amplitude_m":.25,"delta_amplitude_deg":2,"cpu":1,"gpu":False}
ORDER=("N01","N02","N03")
END=dt.datetime(2026,11,5,6,50,tzinfo=dt.timezone(dt.timedelta(hours=1))).timestamp()
START=dt.datetime(2026,11,4,20,45,tzinfo=dt.timezone(dt.timedelta(hours=1))).timestamp()
STATE=HERE/"NIGHT_COMEBACK_STATUS.json"

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def write(p, obj):
    temp=p.with_suffix(".tmp")
    temp.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding="utf8")
    temp.replace(p)

def load_readiness():
    required={"empty_a25":"PASS_POC_NOT_QUANTITATIVE_VALIDATION",
              "kinematics":"PASS_KINEMATICS_ONLY","calm_active":"PASS_DIAGNOSTIC_SMOKE",
              "fixed_a25":"PASS_POC_NOT_QUANTITATIVE_VALIDATION","active_a25":"PASS_DIAGNOSTIC_SMOKE",
              "transport_reopen":"PASS_FIELDS_REOPENED"}
    ready=read(HERE/"NIGHT_READY.json")
    for gate, expected in required.items():
        record=ready["evidence"][gate]
        p=Path(record["path"])
        if not p.resolve().is_relative_to(HERE.resolve()) or sha(p)!=record["sha256"]:
            raise ValueError("Readiness evidence path/hash mismatch: "+gate)
        if read(p)["status"]!=expected:
            raise ValueError("Readiness gate not passed: "+gate)
    source=Path(ready["checkpoint"]["path"])
    if not source.resolve().is_relative_to(HERE.resolve()) or source.name!="FINAL.sim" or sha(source)!=ready["checkpoint"]["sha256"]:
        raise ValueError("Invalid fixed foil checkpoint")
    if ready["parameters"]!=PARAMETERS:
        raise ValueError("Night physics/CPU contract mismatch")
    h=csv_rows(source.parent/"history.csv")
    native=read(source.parent/"SOLVE_STATUS.json")
    if not h or abs(float(h[-1]["time_s"])-float(native["time_s"]))>1e-9:
        raise ValueError("Fixed checkpoint and history time do not agree")
    for mode in ("fixed","active"):
        m=ready["timing"][mode]
        if not all(math.isfinite(float(m[k])) and float(m[k])>0 for k in ("dt_s","wall_s_per_step","startup_s","checkpoint_s")):
            raise ValueError("Missing measured wall timing: "+mode)
    return ready,source

def cost(metrics, kept, discard):
    n=math.ceil((kept+discard)*T/metrics["dt_s"])
    return metrics["startup_s"]+n*metrics["wall_s_per_step"]+(kept+discard+2)*metrics["checkpoint_s"]

def phases(run, start):
    g=[row for row in csv_rows(run/"gauges.csv") if float(row["x_m"])==.952 and float(row["time_s"])>=start-1e-9]
    t=np.array([float(row["time_s"]) for row in g])
    y=np.array([float(row["eta_actual_m"]) for row in g])
    _, z, _=harmonic(t,y)
    if abs(z)<.20:
        raise ValueError("Cannot define a local phase at small amplitude")
    return float(-np.angle(z/np.exp(-1j*K*.952)))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=("forecast","start","status"))
    action=parser.parse_args().action
    if action=="status":
        print(STATE.read_text(encoding="utf8") if STATE.exists() else "HOLD: night not started")
        return
    ready,source=load_readiness()
    timing=ready["timing"]
    if action=="forecast":
        print(json.dumps({mode:{n:round(cost(m,n,1 if mode=="fixed" else 2)/60,1) for n in (1,3,5)}
                          for mode,m in timing.items()},indent=2))
        return
    approved=read(HERE/"NIGHT_APPROVAL_20261104.json")
    authorized=tuple(approved["ordered_run_ids"])
    if (approved.get("approved_by_user") is not True or authorized!=ORDER[:len(authorized)] or
        not authorized or approved.get("readiness_sha256")!=sha(HERE/"NIGHT_READY.json")):
        raise ValueError("Night start requires explicit approved scope and exact readiness file")
    if not START<=time.time()<END or STOP.exists() or STATE.exists():
        raise ValueError("Night start closed, stopped, or already attempted")
    protected_idle()
    with LOCK.open("x",encoding="ascii") as lock:
        import os
        lock.write(str(os.getpid()))
    summary=dict(operation="STARTED",approved_runs=authorized,runs={})
    write(STATE,summary)
    try:
        checkpoint=source
        offset=0.
        for stage in authorized:
            protected_idle()
            active=stage!="N01"
            mode="active" if active else "fixed"
            discard=2 if active else 1
            kept=3
            m=timing[mode]
            wall=int(math.ceil(1.2*cost(m,kept,discard)))
            if time.time()+wall+90>=END:
                raise RuntimeError("Insufficient night time for full analysis window: "+stage)
            previous=read(checkpoint.parent/"SOLVE_STATUS.json")
            t0=float(previous["time_s"])
            analyze=t0+discard*T
            result=new_job(stage,dict(source=checkpoint,expected_time=t0,foil=True,moving=active,night=True,
                authorization="COMEBACK_NIGHT_APPROVED",amplitude=.25,old_amplitude=.25,dt=m["dt_s"],
                steps=math.ceil((discard+kept)*T/m["dt_s"]),limit_seconds=wall,control_phase_rad=math.pi/2 if stage=="N03" else 0,
                phase_offset_rad=offset,motion_ramp_s=T))
            run=Path(result["checkpoint"]).parent
            summary["runs"][stage]=result
            write(STATE,summary)
            if not result["transport_ok"] or result["status"]!="NUMERICAL_END_PASS":
                raise RuntimeError("Native solver did not pass: "+stage)
            science=wave_review(run,.25,analyze,cycles=kept,foil=True)
            if not science["pass"]:
                raise RuntimeError("Wave and force gates did not pass: "+stage)
            if active:
                for row in csv_rows(run/"history.csv"):
                    if abs(float(row["delta_measured_deg"])-float(row["delta_command_deg"]))>.08:
                        raise RuntimeError("Active phase/tracking gate failed")
            local=phases(run,analyze)
            write(run/"DATASET_ACCEPTANCE.json",dict(status="ACCEPTED",run_id=run.name,
                analysis_start_s=analyze,analysis_end_s=analyze+kept*T,local_phase_offset_rad=local,
                sha256={f:sha(run/f) for f in ("FINAL.sim","history.csv","gauges.csv")}))
            export(run,run/"DATASET_ACCEPTED","ACCEPTED","SEALED_FOIL_Q2D_44442")
            summary["runs"][stage]["science"]="ACCEPTED"
            write(STATE,summary)
            if stage=="N01":
                checkpoint=run/"FINAL.sim"
                offset=local
        summary["operation"]="COMPLETE"
    except Exception as err:
        summary.update(operation="HOLD",reason=str(err))
        raise
    finally:
        write(STATE,summary)
        LOCK.unlink()

if __name__=="__main__":
    main()

