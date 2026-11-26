"""Finite daytime queue. It waits for independent jobs and never enables night runs."""
import datetime as dt
import json
import math
from pathlib import Path
import time

import numpy as np
from run_day import HERE, LOCK, STOP, STAGES, new_job, protected_idle, status, independent_jobs, sha, query, READ
from review_native_motion import check as motion_review
from export_trajectory import csv_rows, export

DAY_END = dt.datetime(2026,11,4,20,15,tzinfo=dt.timezone(dt.timedelta(hours=1))).timestamp()
SUMMARY = HERE/"DAY_QUEUE.json"

def save(data):
    temp=SUMMARY.with_suffix(".tmp")
    temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf8")
    temp.replace(SUMMARY)

def compare_reopen(previous, folder):
    a=np.loadtxt(previous/"field_end.csv",delimiter=",",skiprows=1)
    b=np.loadtxt(folder/"reopened_fields.csv",delimiter=",",skiprows=1)
    meta=json.loads((folder/"REOPEN.json").read_text(encoding="utf8"))
    if a.shape!=b.shape or len(b)!=meta["cells"] or not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise ValueError("Invalid reopened full-field data")
    def sorted_rows(x):
        return x[np.lexsort((x[:,-1],x[:,-2],x[:,-3]))]
    a,b=sorted_rows(a),sorted_rows(b)
    if not np.allclose(a,b,rtol=1e-10,atol=1e-9):
        raise ValueError("Reopened fields differ")
    expected=json.loads((previous/"SOLVE_STATUS.json").read_text(encoding="utf8"))["time_s"]
    if not math.isclose(meta["time_s"],expected,abs_tol=1e-12):
        raise ValueError("Reopened time differs")
    return dict(status="PASS_FIELDS_REOPENED",cells=meta["cells"],time_s=meta["time_s"],
                max_abs_difference=float(abs(a-b).max()),source_sha256=sha(previous/"FINAL.sim"))

def wait_idle(summary, cutoff):
    while not STOP.exists() and time.time()<cutoff:
        try:
            protected_idle()
            # Ensure absence of pending work twice before starting STAR.
            time.sleep(10)
            protected_idle()
            return True
        except RuntimeError as err:
            summary["operation"]="WAIT_INDEPENDENT_QUEUE"
            summary["reason"]=str(err)
            save(summary)
            time.sleep(30)
    return False

def main():
    with LOCK.open("x",encoding="ascii") as f:
        import os
        f.write(str(os.getpid()))
    try:
        if SUMMARY.exists():
            raise ValueError("Existing daytime queue history. Refuse replay.")
        summary=dict(operation="QUEUED_DAY_TESTS",night_authorized=False,solver_state="STOPPED",runs={})
        save(summary)
        cutoff=min(DAY_END,time.time()+2*3600)
        stages=[(k,v) for k,v in STAGES.items()]
        failures=0
        motion_ok=False
        motion_flow_ok=False
        for stage,params in stages:
            if failures>=2 or not wait_idle(summary,cutoff):
                break
            summary.update(operation="STARTING_DAY_TEST",stage=stage,reason="")
            save(summary)
            try:
                result=new_job(stage,{**params,"limit_seconds":min(720,int(DAY_END-time.time()))})
                folder=Path(result["checkpoint"]).parent
                summary["runs"][stage]=result
                if result["transport_ok"] is not True:
                    failures+=1
                if stage=="A05_SMOKE" and result["transport_ok"] and result["samples"]==40:
                    if wait_idle(summary,cutoff):
                        reopened=new_job("A05_REOPEN",dict(source=folder/"FINAL.sim",verify=True,steps=0))
                        review=compare_reopen(folder,Path(reopened["run_directory"]))
                        summary["runs"]["A05_REOPEN"]=review
                if stage=="B_KINEMATICS" and result["transport_ok"]:
                    review=motion_review(folder)
                    summary["runs"][stage]["kinematic_review"]=review
                    motion_ok=review["status"]=="PASS_KINEMATICS_ONLY"
                if stage=="B_KINEMATICS" and motion_ok and wait_idle(summary,cutoff):
                    active=new_job("B_SINGLE_PHASE_SMOKE",dict(fresh=True,foil=True,moving=True,single_phase=True,
                        expected_time=0,amplitude=0,old_amplitude=0,steps=40,motion_ramp_s=.10,
                        control_phase_rad=1.57,u_diagnostic_m_s=10))
                    summary["runs"]["B_SINGLE_PHASE_SMOKE"]=active
                    motion_flow_ok=(active["transport_ok"] and active["status"]=="PASS_DIAGNOSTIC_SMOKE")
                if stage=="I0_CALM_SMOKE" and result["transport_ok"] and result["status"]=="NUMERICAL_END_PASS":
                    a_reopen=summary["runs"].get("A05_REOPEN",{}).get("status")
                    a_result=summary["runs"].get("A05_SMOKE",{})
                    wave_safe=a_result.get("status") in ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW")
                    if a_reopen=="PASS_FIELDS_REOPENED" and wave_safe and wait_idle(summary,cutoff):
                        # Globally initialized A=.05 m on the foil mesh. Startup diagnostic, no periodic claim.
                        i1=new_job("I1_A05_FIXED_DIAGNOSTIC",dict(fresh=True,foil=True,expected_time=0,
                            amplitude=.05,old_amplitude=.05,steps=40))
                        summary["runs"]["I1_A05_FIXED_DIAGNOSTIC"]=i1
                        source=Path(i1["checkpoint"])
                        if i1["samples"]:
                            export(source.parent,source.parent/"DATASET_DIAGNOSTIC","DIAGNOSTIC","SEALED_FOIL_Q2D_44442")
                        if i1["transport_ok"] and i1["status"]=="NUMERICAL_END_PASS" and motion_flow_ok and wait_idle(summary,cutoff):
                            i2=new_job("I2_A05_ACTIVE_DIAGNOSTIC",dict(source=source,foil=True,moving=True,
                                expected_time=i1["state"]["time_s"],amplitude=.05,old_amplitude=.05,
                                steps=40,motion_ramp_s=.10,control_phase_rad=1.57))
                            summary["runs"]["I2_A05_ACTIVE_DIAGNOSTIC"]=i2
                            out=Path(i2["checkpoint"]).parent
                            if i2["samples"]:
                                export(out,out/"DATASET_DIAGNOSTIC","DIAGNOSTIC","SEALED_FOIL_Q2D_44442")
                if (folder/"history.csv").exists() and result["samples"]:
                    export(folder,folder/"DATASET_DIAGNOSTIC","DIAGNOSTIC",
                           "SEALED_FOIL_Q2D_44442" if params.get("foil") else "NATIVE_EMPTY_Q2D_41280")
            except Exception as err:
                summary["runs"].setdefault(stage,{})["day_error"]=str(err)
                failures+=1
            save(summary)
        summary.update(operation="DAY_TESTS_ENDED",solver_state="HOLD" if STOP.exists() else "STOPPED",
                       night_authorized=False,transport_or_setup_failures=failures)
        save(summary)
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()



