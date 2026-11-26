"""Reuse the existing Mini runner for the conditional daytime sprint."""
import json
import math
from pathlib import Path
import time

from run_sprint import run
from run_day import HERE, LOCK, STOP, sha
from export_trajectory import csv_rows, export
from review_native_motion import coordinates,distance_max
from audit_motion_map import map_vertices
from review_stokes import theoretical_period,review
import stokes_coexistence as coex
import numpy as np

STATE=HERE/"INTEGRATION_SPRINT_STATUS.json"
A=HERE/"SPRINT_A_RAMP40_SPRINT.json"
T=theoretical_period()
RAMP=2*T

def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def basic(outcome,n):
    return outcome.get("transport_ok") and outcome.get("samples")==n and outcome.get("status")=="NUMERICAL_END_PASS"

def review_b(runfolder):
    rows=csv_rows(runfolder/"single_phase.csv")
    moved=[r for r in rows if float(r["time_s"])>.185+1e-8]
    origin=coordinates(runfolder/"vertices_0000.csv")
    final=coordinates(runfolder/"vertices_final.csv")
    angle=float(rows[-1]["delta_command_deg"])
    expected=np.column_stack((map_vertices(origin[:,:2],angle),origin[:,2]))
    error=distance_max(expected,final)
    actual=[float(r["delta_measured_deg"]) for r in moved]
    m=dict(vertex_error_m=error,moving_steps=len(moved),maximum_abs_deg=max(map(abs,actual),default=0),
        pABS_min_Pa=min(float(r["pABSmin_Pa"]) for r in rows),max_CFL=max(float(r["max_CFL"]) for r in rows),
        min_volume_m3=min(float(r["volume_min"]) for r in rows),timestep_s=.001)
    m["pass_geometry"]=error<=2e-5 and len(moved)==40 and m["maximum_abs_deg"]>.15
    coex.save(runfolder/"SINGLE_PHASE_REVIEW.json",m)
    return m

def report(state):
    state["night_authorized"]=False
    coex.save(STATE,state)

def main():
    if STATE.exists():
        raise RuntimeError("Refuse replay of sprint")
    state=dict(operation="WAIT_A_RAMP40",A="WAIT",B="PENDING",C="BLOCKED")
    report(state)
    until=time.monotonic()+700
    while (LOCK.exists() or not A.exists()) and not STOP.exists() and time.monotonic()<until:
        time.sleep(5)
    if LOCK.exists() or STOP.exists() or not A.exists():
        state.update(operation="HOLD",reason="Prior stage/STOP")
        report(state)
        return
    short=read(A).get("result",{})
    state["A_short"]=short
    state["A"]="SMOKE_PASS" if basic(short,40) else "HOLD"
    state["operation"]="B_GENTLE_URANS"
    report(state)
    try:
        b=run("SPRINT_B_GENTLE_URANS",dict(fresh=True,stokes=True,foil=True,moving=True,single_phase=True,
            expected_time=0,amplitude=0,old_amplitude=0,steps=225,limit_seconds=2100,
            motion_start_delay_s=.185,motion_ramp_s=.10,control_phase_rad=1.57,
            u_diagnostic_m_s=10,u_initial_m_s=.02,u_ramp_s=.15))
        state["B_result"]=b
        if b["status"]=="PASS_DIAGNOSTIC_SMOKE" and b["transport_ok"]:
            state["B_review"]=review_b(Path(b["checkpoint"]).parent)
            state["B"]="PASS_DIAGNOSTIC_SMOKE" if state["B_review"]["pass_geometry"] else "HOLD_GEOMETRY"
        else:
            state["B"]="HOLD"
    except Exception as err:
        state["B"]="HOLD"
        state["B_error"]=str(err)
    report(state)
    if not basic(short,40) or STOP.exists():
        state["operation"]="HOLD"
        report(state)
        return
    continue_after_ab(state,short)

def continue_after_ab(state,short):
    cp=Path(short["checkpoint"])
    if sha(cp)!=short["checkpoint_sha256"]:
        raise RuntimeError("A smoke checkpoint hash mismatch")
    start=float(short["state"]["time_s"])
    settle=RAMP+28/(10/T)
    steps=math.ceil((settle+3*T-start)/.001)+2
    samples=csv_rows(cp.parent/"step_wall.csv")
    step_wall=float(np.mean([float(r["step_wall_s"]) for r in samples[5:]]))
    state.update(operation="A_PROPAGATION",A_planned_steps=steps,A_estimated_wall_minutes=(steps*step_wall+150)/60)
    report(state)
    try:
        a=run("SPRINT_A_PROPAGATION",dict(source=cp,stokes=True,expected_time=start,
            amplitude=.25,old_amplitude=0,ramp_s=RAMP,ramp_origin_s=0,steps=steps,
            analysis_start_s=settle,limit_seconds=math.ceil(steps*step_wall*1.35+400)))
        state["A_result"]=a
        target=Path(a["checkpoint"]).parent
        if a["samples"]:
            state["A_review"]=review(target)
        state["A"]="PASS_PROPAGATION" if basic(a,steps) and state.get("A_review",{}).get("status")=="PASS_PROPAGATION" else "HOLD"
    except Exception as err:
        state["A"]="HOLD"
        state["A_error"]=str(err)
    report(state)
    if state["A"]!="PASS_PROPAGATION" or state["B"]!="PASS_DIAGNOSTIC_SMOKE" or STOP.exists():
        state["operation"]="HOLD"
        report(state)
        return
    continue_c(state)

def continue_c(state):
    try:
        state["operation"]="C_H010_FIXED"
        report(state)
        fixed=run("SPRINT_C_H010_FIXED",dict(fresh=True,stokes=True,foil=True,expected_time=0,
            amplitude=.05,old_amplitude=.05,steps=40))
        state["C_fixed"]=fixed
        report(state)
        if basic(fixed,40) and not STOP.exists():
            state["operation"]="C_H010_ACTIVE"
            report(state)
            active=run("MINI_Q2D_STOKES5_ACTIVE_FLAP_H010_SMOKE",dict(source=Path(fixed["checkpoint"]),
                stokes=True,foil=True,moving=True,expected_time=float(fixed["state"]["time_s"]),
                amplitude=.05,old_amplitude=.05,motion_ramp_s=.10,control_phase_rad=1.57,steps=40))
            state["C_active"]=active
            folder=Path(active["checkpoint"]).parent
            if active["samples"]:
                export(folder,folder/"DATASET_DIAGNOSTIC","DIAGNOSTIC","SEALED_FOIL_Q2D_44442")
            state["C"]="PASS_DIAGNOSTIC_SMOKE" if basic(active,40) else "HOLD"
        else:
            state["C"]="HOLD"
    except Exception as err:
        state["C"]="HOLD"
        state["C_error"]=str(err)
    state["operation"]="SPRINT_REVIEW"
    report(state)

if __name__=="__main__":
    main()



