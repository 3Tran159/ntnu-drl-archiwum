import csv
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
CONTROL=PROJECT/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"
sys.path.insert(0,str(CONTROL))
import run as campaign

MARKER="User-authorized pause for native AF reports, monitors, plots and VOF history."
MACRO=HERE/"MiniVofStokes.java"
DAY=PROJECT/"DAY_STATUS.json"
DT=campaign.DT

def status(state, **kwargs):
    campaign.status(state,**kwargs)
    campaign.coex.save(HERE/"AF_CHANGE_STATUS.json",state)

def change():
    live=campaign.read(DAY)
    state=campaign.read(campaign.STATE)
    if (live["stage"]!=campaign.FIXED or live["solver_state"]!="RUNNING" or
        state["status"]!="RUNNING" or state["motion_authorized"] or not campaign.LOCK.is_file()):
        raise RuntimeError("Expected owned active fixed VOF stage")
    original=Path(live["output"])
    state={"status":"SAVING","stage":campaign.FIXED,"operation":"AF_CHANGE_AT_CHECKPOINT",
           "previous_run":str(original),"motion_authorized":False}
    campaign.coex.save(HERE/"AF_CHANGE_STATUS.json",state)
    with campaign.STOP.open("x",encoding="ascii") as f:
        f.write(MARKER)
    expires=time.monotonic()+300
    while (campaign.LOCK.exists() or campaign.filtered_query(campaign.OWNER)):
        if time.monotonic()>expires:
            raise RuntimeError("Timed out waiting for owned solver checkpoint and exit")
        time.sleep(3)
    completed=campaign.read(campaign.STATE)
    result=completed["fixed_result"]
    source=Path(result["archive"])/"FINAL.sim"
    if (result["status"]!="HOLD_STOP_OR_DEADLINE" or not result["transport_ok"] or
        not source.is_file() or campaign.sha(source)!=result["checkpoint_sha256"]):
        raise RuntimeError("Graceful checkpoint did not verify")
    rows=campaign.tail(original/"history.csv")
    end=result["state"]["time_s"]
    if not rows or abs(float(rows[-1]["time_s"])-end)>1e-9:
        raise RuntimeError("History does not match native checkpoint")
    window=round(.05/DT)
    used=len(rows)
    checkpoint_gate=original/"CALM_FIXED_PROGRESS.json"
    gate=campaign.read(checkpoint_gate) if checkpoint_gate.is_file() else {"stable_windows":0}
    seed_count=window+used%window
    if len(rows)<seed_count:
        raise RuntimeError("Missing preceding stabilization window")
    rows=rows[-seed_count:]
    if any(abs(float(r["delta_measured_deg"]))>1e-10 or abs(float(r["delta_command_deg"]))>1e-10 or
           abs(float(r["time_s"])-(end-(seed_count-1-i)*DT))>1e-9 for i,r in enumerate(rows)):
        raise RuntimeError("Checkpoint or preceding stabilization window invalid")
    seed=HERE/"AF_FIXED_RESUME_WINDOW.csv"
    with seed.open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=("time_s","CL","CD"),extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    if campaign.STOP.read_text().strip()!=MARKER:
        raise RuntimeError("STOP marker ownership changed")
    with campaign.LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    try:
        campaign.STOP.rename(HERE/"AF_PAUSE_REQUEST_ARCHIVED.txt")
        checkpoint_sha=campaign.sha(source)
        status(state,status="RUNNING",operation="STARTING_FROM_AF_CHECKPOINT",
               source=str(source),start_s=end,checkpoint_sha256=checkpoint_sha,
               seeded_samples=seed_count,carried_stable_windows=gate["stable_windows"])
        settings={"stokes":True,"foil":True,"expected_cells":17462,"calm_only":True,
                  "clean_calm":True,"matched_calm":True,"pressure_diagnostic_only":True,
                  "amplitude":0,"old_amplitude":0,"dt":DT,"inner":20,"save_interval_s":.05,
                  "af_native":True}
        def job(stage, options):
            return campaign.new_job(stage,{**settings,**options},
                  protection=campaign.NightGuard(None,1.777749),macro_source=MACRO,mpi_cpu_indices=campaign.CPUS)
        fixed_result=job(campaign.FIXED,dict(source=source,expected_time=end,matched_calm_fixed=True,
            moving=False,steps=6000-used,fixed_window_seed=seed.as_posix(),fixed_stable_count=gate["stable_windows"],
            limit_seconds=21600))
        fixed=campaign.publish(fixed_result)
        state["fixed_result"]=fixed_result
        gate=fixed_result.get("stabilization",{})
        verified=(fixed_result["status"]=="PASS_CALM_FORCE_STABILIZATION" and fixed_result["transport_ok"]
              and gate.get("stable_windows")==3 and gate["CL_drift_fraction"]<.005 and gate["CD_drift_fraction"]<.005
              and abs(gate["time_s"]-fixed_result["state"]["time_s"])<1e-9
              and campaign.sha(fixed/"FINAL.sim")==fixed_result["checkpoint_sha256"])
        if not verified or campaign.STOP.exists():
            status(state,status="HOLD",operation="AF_FIXED_GATE_NOT_PASSED",stage=None)
            return
        last=campaign.tail(fixed/"history.csv")[-1]
        if any(abs(float(last[k]))>1e-10 for k in ("delta_measured_deg","delta_command_deg")):
            raise RuntimeError("Stabilized state is not fixed at 0 degrees")
        status(state,stage=campaign.MOTION,operation="STARTING_MOTION",motion_authorized=True,
               stable_checkpoint=str(fixed/"FINAL.sim"))
        motion=job(campaign.MOTION,dict(source=fixed/"FINAL.sim",expected_time=gate["time_s"],moving=True,
            flow_cycle=True,calm_active_pilot=True,flap_cycle_deg=5,flap_quarter_s=.125,steps=2500,limit_seconds=18000))
        campaign.publish(motion)
        status(state,status="REVIEW",operation="MOTION_FINISHED",stage=None,motion_result=motion)
    except Exception as e:
        status(state,status="HOLD",operation="AF_CONFIGURATION_ERROR",reason=str(e))
        raise
    finally:
        if not campaign.filtered_query(campaign.OWNER):
            campaign.LOCK.unlink()

if __name__=="__main__":
    change()

