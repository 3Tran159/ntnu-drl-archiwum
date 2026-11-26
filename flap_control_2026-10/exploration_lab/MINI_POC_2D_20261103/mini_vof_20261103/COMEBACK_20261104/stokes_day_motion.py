"""Continue the existing Mini day track under the measured 15% W06 hard-stop policy."""
import csv
import json
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job
from review_native_motion import check

TRIAL=HERE/"W06_STOKES_TRIAL.json"
STATUS=HERE/"STOKES_MOTION_STATUS.json"
coex.BASELINE_FILE=HERE/"W06_MOTION_BASELINE.json"
coex.WATCH=HERE/"W06_MOTION_WATCH.csv"

def main():
    proof=json.loads(TRIAL.read_text(encoding="utf8"))
    if (not proof.get("license_granted") or proof.get("reason") or
        not proof["result"]["transport_ok"] or proof["distinct_active_W06_measurements"]<4 or
        proof["max_rolling_slowdown"]>.15):
        raise RuntimeError("W06 resource observations do not permit another Mini stage")
    if STATUS.exists() or STOP.exists():
        raise RuntimeError("Prior attempt or stop marker")
    with LOCK.open("x",encoding="ascii") as lock:
        import os
        lock.write(str(os.getpid()))
    data=dict(operation="MOTION_DIAGNOSTIC",night_authorized=False,wave_branch="HOLD_TURBULENCE_LIMIT")
    coex.save(STATUS,data)
    try:
        with coex.WATCH.open("x",encoding="ascii",newline="") as f:
            csv.writer(f).writerow(("time","phase","w06_step","w06_physical_s","w06_rolling_median_s","slowdown_fraction","mini_steps"))
        monitor=coex.W06Protection()
        monitor.make_baseline()
        data["baseline_s"]=monitor.baseline
        outcome=new_job("STOKES_B_KINEMATICS",dict(fresh=True,stokes=True,foil=True,moving=True,
            kinematics=True,dt=.005,inner=1,amplitude=0,old_amplitude=0,expected_time=0,steps=40),
            protection=monitor)
        data["kinematics"]=outcome
        data["w06_peak_slowdown"]=monitor.peak
        if monitor.stopped or not outcome["transport_ok"] or outcome["status"]!="MOTION_NATIVE_PENDING_VERTEX_REVIEW":
            raise RuntimeError(monitor.stopped or outcome["status"])
        motion=check(Path(outcome["checkpoint"]).parent)
        data["motion_review"]=motion
        coex.save(STATUS,data)
        if motion["status"]!="PASS_KINEMATICS_ONLY":
            raise RuntimeError("Native vertex verification failed")
        monitor=coex.W06Protection()
        coex.BASELINE_FILE=HERE/"W06_SINGLE_PHASE_BASELINE.json"
        monitor.make_baseline()
        data["single_phase"]=new_job("STOKES_B_SINGLE_PHASE",dict(fresh=True,stokes=True,foil=True,moving=True,
            single_phase=True,expected_time=0,amplitude=0,old_amplitude=0,steps=40,
            motion_ramp_s=.10,control_phase_rad=1.57,u_diagnostic_m_s=10),protection=monitor)
        data["single_phase_w06_peak_slowdown"]=monitor.peak
        data["operation"]="MOTION_TRACK_REVIEW"
    except Exception as err:
        data.update(operation="HOLD",reason=str(err))
        raise
    finally:
        coex.save(STATUS,data)
        LOCK.unlink()

if __name__=="__main__":
    main()

