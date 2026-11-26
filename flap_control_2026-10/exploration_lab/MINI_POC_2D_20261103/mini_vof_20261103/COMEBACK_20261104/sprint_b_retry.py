"""Retry B once with the target ambient SST field, after the current wave work."""
from datetime import datetime, timezone, timedelta
import time
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP
from run_sprint import run
from sprint_followup import STATE, continue_c, read, report, review_b

WAIT=HERE/"SPRINT_B_RETRY_WAIT.json"
WAVE=HERE/"SPRINT_A_RETRY_WAIT.json"
CUTOFF=datetime(2026,11,4,19,30,tzinfo=timezone(timedelta(hours=1))).timestamp()

def main():
    if WAIT.exists():
        raise RuntimeError("B retry already registered")
    coex.save(WAIT,{"operation":"WAIT_FOR_WAVE_RELEASE"})
    while time.time()<CUTOFF and not STOP.exists():
        if not LOCK.exists() and WAVE.exists() and read(WAVE).get("operation")=="FINISHED":
            break
        time.sleep(15)
    if STOP.exists() or LOCK.exists() or time.time()>=CUTOFF:
        coex.save(WAIT,{"operation":"HOLD","reason":"STOP, resources or day cutoff"})
        return
    state=read(STATE)
    old=state.get("B_result",{})
    if old.get("samples")!=3 or old.get("status")!="HOLD_SINGLE_PHASE_SAFETY":
        raise RuntimeError("B failure differs from confirmed startup k-floor event")
    state.update(operation="B_AMBIENT_SST_RETRY",B="RUNNING")
    report(state)
    try:
        b=run("SPRINT_B_AMBIENT_SST_URANS",dict(fresh=True,stokes=True,foil=True,moving=True,
            single_phase=True,expected_time=0,amplitude=0,old_amplitude=0,steps=225,limit_seconds=2100,
            motion_start_delay_s=.185,motion_ramp_s=.10,control_phase_rad=1.57,
            u_diagnostic_m_s=10,u_initial_m_s=.02,u_ramp_s=.15,target_ambient_turbulence=True))
        state["B_corrected"]=b
        if b["status"]=="PASS_DIAGNOSTIC_SMOKE" and b["transport_ok"]:
            q=review_b(Path(b["checkpoint"]).parent)
            state["B_review"]=q
            state["B"]="PASS_DIAGNOSTIC_SMOKE" if q["pass_geometry"] else "HOLD_GEOMETRY"
        else:
            state["B"]="HOLD"
        if state["B"]=="PASS_DIAGNOSTIC_SMOKE" and state["A"]=="PASS_PROPAGATION" and not STOP.exists():
            report(state)
            continue_c(state)
        else:
            state["operation"]="HOLD"
            report(state)
    except Exception as err:
        state.update(operation="HOLD",B="HOLD",B_retry_error=str(err))
        report(state)
    finally:
        coex.save(WAIT,{"operation":"FINISHED"})

if __name__=="__main__":
    main()

