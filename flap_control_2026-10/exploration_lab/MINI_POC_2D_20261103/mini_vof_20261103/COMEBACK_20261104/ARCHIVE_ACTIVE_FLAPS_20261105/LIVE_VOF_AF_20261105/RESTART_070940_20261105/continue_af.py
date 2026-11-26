import csv
import math
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
CONTROL=PROJECT/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"
sys.path.insert(0,str(CONTROL))
import run as campaign

DT=campaign.DT
FAILED=PROJECT/"runs/CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST_20261105_122056"
SOURCE=FAILED/"AF_FIRST_STEP.sim"
SETUP_FAILURE=PROJECT/"runs/CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST_20261105_130240"
SOURCE_SHA="54ebdd92950e103639c52bcf6c105ee378799b992ee186ab1182820646cbd4c8"
CADENCE=.005

def start():
    prior=campaign.read(PROJECT/"DAY_STATUS.json")
    if (prior["solver_state"]!="STOPPED" or Path(prior["output"]) not in (FAILED,SETUP_FAILURE) or
        campaign.STOP.exists() or campaign.LOCK.exists() or campaign.filtered_query(campaign.OWNER)):
        raise RuntimeError("Expected stopped sealed VOF with no stop marker or active owner")
    if Path(prior["output"])==SETUP_FAILURE:
        failure=campaign.read(SETUP_FAILURE/"SOLVE_STATUS.json")
        if failure["steps"]!=0 or "in use by another Solution History" not in failure["error"]:
            raise RuntimeError("Unexpected preceding startup error")
    receipt=campaign.read(FAILED/"LATEST_CHECKPOINT.json")
    time_s=receipt["time_s"]
    if (not receipt["complete_write"] or Path(receipt["path"])!=SOURCE or receipt["step_in_job"]!=1 or
        abs(time_s-.7094)>1e-9 or SOURCE.stat().st_size!=receipt["bytes"] or campaign.sha(SOURCE).lower()!=SOURCE_SHA):
        raise RuntimeError("Requested checkpoint identity or hash failed")
    history=campaign.tail(HERE.parent/"AF_FIXED_RESUME_WINDOW.csv")
    latest=campaign.tail(FAILED/"history.csv")[0]
    if (abs(float(latest["time_s"])-time_s)>1e-9 or latest["step"]!="1" or
        any(abs(float(latest[k]))>1e-10 for k in ("delta_measured_deg","delta_command_deg"))):
        raise RuntimeError("History at requested checkpoint failed")
    history.append(latest)
    if len(history)!=432 or any(abs(float(row["time_s"])-(time_s-(len(history)-1-i)*DT))>1e-9
        or not all(math.isfinite(float(row[k])) for k in ("CL","CD")) for i,row in enumerate(history)):
        raise RuntimeError("Stabilization seed failed")
    seed=HERE/"FIXED_RESUME_WINDOW_RETRY.csv"
    with seed.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=("time_s","CL","CD"),extrasaction="ignore")
        writer.writeheader()
        writer.writerows(history)
    with campaign.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=dict(status="RUNNING",stage=campaign.FIXED,operation="RESTART_FROM_VERIFIED_CHECKPOINT",
               motion_authorized=False,start_s=time_s,source=str(SOURCE),checkpoint_sha256=SOURCE_SHA,
               save_interval_s=CADENCE,seeded_samples=len(history))
    def status(**changes):
        campaign.status(state,**changes)
        campaign.coex.save(HERE/"RESTART_STATUS.json",state)
    settings=dict(stokes=True,foil=True,expected_cells=17462,calm_only=True,clean_calm=True,
                  matched_calm=True,pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,
                  dt=DT,inner=20,save_interval_s=CADENCE,af_native=True)
    def job(stage, **options):
        return campaign.new_job(stage,{**settings,**options},protection=campaign.NightGuard(None,1.777749),
            macro_source=HERE/"MiniVofStokes.java",mpi_cpu_indices=campaign.CPUS)
    try:
        status()
        result=job(campaign.FIXED,source=SOURCE,expected_time=time_s,matched_calm_fixed=True,
            moving=False,steps=5068,fixed_window_seed=seed.as_posix(),fixed_stable_count=0,limit_seconds=21600)
        fixed=campaign.publish(result)
        state["fixed_result"]=result
        gate=result.get("stabilization",{})
        verified=(result["status"]=="PASS_CALM_FORCE_STABILIZATION" and result["transport_ok"] and
            gate.get("stable_windows")==3 and gate["CL_drift_fraction"]<.005 and gate["CD_drift_fraction"]<.005 and
            abs(gate["time_s"]-result["state"]["time_s"])<1e-9 and
            campaign.sha(fixed/"FINAL.sim")==result["checkpoint_sha256"])
        if not verified or campaign.STOP.exists():
            status(status="HOLD",operation="FIXED_GATE_NOT_PASSED",stage=None)
            return
        last=campaign.tail(fixed/"history.csv")[-1]
        if any(abs(float(last[k]))>1e-10 for k in ("delta_measured_deg","delta_command_deg")):
            raise RuntimeError("Fixed checkpoint angle is not zero")
        status(stage=campaign.MOTION,operation="STARTING_MOTION",motion_authorized=True,
               stable_checkpoint=str(fixed/"FINAL.sim"))
        motion=job(campaign.MOTION,source=fixed/"FINAL.sim",expected_time=gate["time_s"],moving=True,
            flow_cycle=True,calm_active_pilot=True,flap_cycle_deg=5,flap_quarter_s=.125,steps=2500,limit_seconds=18000)
        campaign.publish(motion)
        status(status="REVIEW",operation="MOTION_FINISHED",stage=None,motion_result=motion)
    except Exception as err:
        status(status="HOLD",operation="RESTART_INTERRUPTED",reason=str(err))
        raise
    finally:
        if not campaign.filtered_query(campaign.OWNER):
            campaign.LOCK.unlink()

if __name__=="__main__":
    start()

