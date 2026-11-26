import csv
import json
import os
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
import run_local as local
from run_local import A, CPUS, HERE, LOCK, STOP, OWNER, NightGuard, archive, coex, filtered_query, new_job, read, sha

P=A/"NIGHT_FLAP_20261104/CALM_VOF_FIXED_SEALED_DT020_WMI_RESUME"
O=A/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"
STATE=D/"STATUS.json"
FIXED="CALM_VOF_SHARP_SEALED_0_STABILIZE_FIRST"
MOTION="CALM_VOF_SHARP_SEALED_PLUS_MINUS_5_AFTER_STABLE"
MARKER="User requested fixed VOF stabilization before flap motion, 2026-11-05."
DT=.0002

def status(state,**values):
    state.update(values)
    coex.save(STATE,state)

def tail(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

def publish(result):
    run=Path(result["checkpoint"]).parent
    dest=O/run.name
    dest.mkdir()
    for name in ("FINAL.sim","history.csv","gauges.csv","PRESSURE_BELOW_VAPOR.csv","DAY_RESULT.json",
                 "SOLVE_STATUS.json","RESIDUAL_FINAL25.json","LATEST_CHECKPOINT.json","CALM_FIXED_PROGRESS.json"):
        if (run/name).is_file():
            archive(run/name,dest/name)
    result["archive"]=str(dest)
    if (dest/"CALM_FIXED_PROGRESS.json").is_file():
        result["stabilization"]=read(dest/"CALM_FIXED_PROGRESS.json")
    coex.save(dest/"RESULT.json",result)
    return dest


def run(stage,opts):
    settings=dict(stokes=True,foil=True,expected_cells=17462,calm_only=True,clean_calm=True,
                  matched_calm=True,pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,
                  dt=DT,inner=20,save_interval_s=.05,**opts)
    return new_job(stage,settings,protection=NightGuard(None,1.777749),
                   macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)


def main():
    prior=read(P/"RESULT.json")
    source=P/"FINAL.sim"
    start=prior["state"]["time_s"]
    old=read(D.parent/"STATUS.json")["jobs"]["CALM_VOF_SHARP_SEALED_PLUS_MINUS_5"]
    if (sha(source)!=prior["checkpoint_sha256"] or old["status"]!="HOLD_STOP_OR_DEADLINE"
        or not old["transport_ok"] or sha(Path(old["archive"])/"FINAL.sim")!=old["checkpoint_sha256"]):
        raise RuntimeError("Old fixed and interrupted active checkpoints not verified")
    if filtered_query(OWNER) or STOP.read_text().strip()!=MARKER:
        raise RuntimeError("Unexpected STOP or active Mini listener")
    history=tail(P/"history.csv")[-250:]
    if len(history)!=250 or abs(float(history[-1]["time_s"])-start)>1e-9 or any(
            abs(float(r["delta_measured_deg"]))>1e-10 or abs(float(r["delta_command_deg"]))>1e-10
            for r in history):
        raise RuntimeError("Source fixed window is not at 0 degrees or checkpoint does not match")
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=dict(status="RUNNING",stage=FIXED,source=str(source),start_s=start,motion_authorized=False)
    try:
        O.mkdir()
        marker=D/"EARLY_MOTION_STOP_ARCHIVED.txt"
        if marker.exists() or STOP.read_text().strip()!=MARKER:
            raise RuntimeError("Unexpected user stop marker")
        STOP.rename(marker)
        archive(marker,O/marker.name)
        seed=D/"PREVIOUS_FIXED_WINDOW.csv"
        with seed.open("x",newline="") as f:
            w=csv.DictWriter(f,fieldnames=("time_s","CL","CD"),extrasaction="ignore")
            w.writeheader();w.writerows(history)
        status(state)
        result=run(FIXED,dict(source=source,expected_time=start,matched_calm_fixed=True,
                              moving=False,steps=6000,fixed_window_seed=seed.as_posix(),limit_seconds=21600))
        fixed=publish(result)
        state["fixed_result"]=result
        gate=result.get("stabilization",{})
        verified=(result["status"]=="PASS_CALM_FORCE_STABILIZATION" and result["transport_ok"]
                  and gate.get("stable_windows")==3 and gate["CL_drift_fraction"]<.005 and gate["CD_drift_fraction"]<.005
                  and abs(gate["time_s"]-result["state"]["time_s"])<1e-9 and sha(fixed/"FINAL.sim")==result["checkpoint_sha256"])
        if not verified or STOP.exists():
            status(state,status="HOLD",stage=None,reason="Fixed VOF force stabilization or checkpoint gate not passed")
            return
        final=tail(fixed/"history.csv")[-1]
        if abs(float(final["delta_measured_deg"]))>1e-10 or abs(float(final["delta_command_deg"]))>1e-10:
            raise RuntimeError("Stabilized state is not fixed at 0 degrees")
        status(state,stage=MOTION,motion_authorized=True,stable_checkpoint=str(fixed/"FINAL.sim"))
        motion=run(MOTION,dict(source=fixed/"FINAL.sim",expected_time=gate["time_s"],moving=True,
            flow_cycle=True,calm_active_pilot=True,flap_cycle_deg=5,flap_quarter_s=.125,steps=2500,
            limit_seconds=18000))
        publish(motion)
        status(state,status="REVIEW",stage=None,motion_result=motion)
    except Exception as err:
        status(state,status="HOLD",reason=str(err))
        raise
    finally:
        if not filtered_query(OWNER):
            LOCK.unlink()

if __name__=="__main__":
    main()

