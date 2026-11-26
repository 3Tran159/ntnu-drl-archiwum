import csv
import json
import os
from pathlib import Path
import subprocess
import sys

D=Path(__file__).resolve().parent
P=D.parent
sys.path.insert(0,str(P/"NIGHT_FLAP_20261104"))
from night_flap import NightGuard,CPUS,HERE,LOCK,STOP,OWNER,archive,coex,new_job,query,sha
import night_flap
import run_day

A=Path(r"T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104")
O=A/"FLAP_EXTREMA_VOF5_20261105"
runs=P/"runs"
gap=runs/"MATCHED_FIXED_GAP_RESUME0600_STABILIZE_THEN_ACTIVE_20261104_200827"
sealed=runs/"MATCHED_FIXED_SHARP_SEALED_ACTIVE_RESUME_1064_20261104_173950"
night=A/"NIGHT_FLAP_20261104"
jobs=(
 ("GAP_MINUS2",gap/"ACTIVE_STEP0200.sim",1.,1.05,1.05,-2.,19502,True),
 ("GAP_PLUS2",A/"GAP_MATCHED_STABILIZE_THEN_ACTIVE_RESUME0600/FINAL.sim",1.,1.133,1.15,2.,19502,True),
 ("SEALED_MINUS2",A/"SHARP_SEALED_ACTIVE_PAUSE_1P064S.sim",1.05,1.064,1.10,-2.,17462,False),
 ("SEALED_PLUS2",sealed/"ACTIVE_STEP0400.sim",1.05,1.164,1.20,2.,17462,False),
)
state={"status":"RUNNING","stage":None,"jobs":{}}

def update(**keys):
    state.update(keys)
    coex.save(D/"STATUS.json",state)

def read(file):
    return json.loads(file.read_text(encoding="utf-8-sig"))

def filtered_query(code):
    result=subprocess.run(["powershell","-NoProfile","-Command",code],capture_output=True,
        text=True,check=True,timeout=60,creationflags=run_day.FLAG)
    v=json.loads(result.stdout.strip() or "[]")
    return v if isinstance(v,list) else [v]

filter_names=" OR ".join(f"Name='{name}'" for name in
    ("starccm+.exe","starccm+w.exe","star-ccm+.exe","smpd.exe","mpiexec.exe","impi.exe"))
run_day.READ="$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process -Filter \""+filter_names+"\" | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath) | ConvertTo-Json -Compress"
night_flap.READ=run_day.READ
run_day.query=filtered_query
night_flap.query=filtered_query

def launch_snapshot(item):
    label,source,origin,start,finish,angle,cells,is_gap=item
    steps=round((finish-start)/.00025)
    if not source.is_file() or abs(start+steps*.00025-finish)>1e-9:
        raise RuntimeError("Missing or invalid source checkpoint")
    guard=NightGuard(None,1.777749)
    opts=dict(source=source,expected_time=start,expected_cells=cells,snapshot_time=finish,snapshot_angle=angle,limit_seconds=1700)
    if not steps:
        opts.update(verify=True,steps=0,pressure_snapshot_only=True)
        result=new_job("SNAPSHOT_"+label,opts,protection=guard,macro_source=D/"VerifyComeback.java",mpi_cpu_indices=CPUS)
        run=Path(result["run_directory"])
    else:
        opts.update(stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,
            resume_coarse_active=True,motion_origin_s=origin,reference_tip_x_m=1.19,reference_tip_y_m=0,
            flow_cycle=True,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.00025,
            steps=steps,seeded_single_phase=True,gapped_geometry=is_gap,fixed_from_unsteady=True,
            pressure_diagnostic_only=True,pressure_snapshot_replay=True)
        result=new_job("SNAPSHOT_"+label,opts,protection=guard,macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
        run=Path(result["checkpoint"]).parent
        if not result["transport_ok"] or result["status"]!="PASS_DIAGNOSTIC_SMOKE" or result["samples"]!=steps:
            raise RuntimeError(f"Snapshot replay incomplete: {result['status']}")
        with (run/"single_phase.csv").open(newline="") as f:
            last=list(csv.DictReader(f))[-1]
        if abs(float(last["delta_measured_deg"])-angle)>1e-7:
            raise RuntimeError("Unexpected measured angle")
    receipt=read(run/"REOPEN.json")
    if abs(receipt["time_s"]-finish)>1e-9:
        raise RuntimeError("Snapshot time mismatch")
    dest=O/label
    dest.mkdir()
    for name in ("native_pressure.png","pressure_flap.csv","REOPEN.json","FINAL.sim","single_phase.csv"):
        if (run/name).is_file():
            archive(run/name,dest/name)
    return dict(receipt,source=str(source),source_sha256=sha(source),archive=str(dest),status="SAVED")


def vof():
    base=night/"CALM_VOF_FIXED_SEALED_DT020_WMI_RESUME"
    source=base/"FINAL.sim"
    prior=read(base/"RESULT.json")
    if sha(source)!=prior["checkpoint_sha256"]:
        raise RuntimeError("Sealed calm VOF input SHA mismatch")
    opts=dict(source=source,expected_time=prior["state"]["time_s"],expected_cells=17462,stokes=True,
              foil=True,moving=True,flow_cycle=True,calm_only=True,clean_calm=True,matched_calm=True,
              calm_active_pilot=True,pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,dt=.0002,inner=20,
              flap_cycle_deg=5,flap_quarter_s=.125,save_interval_s=.05,steps=2500,limit_seconds=18000)
    guard=NightGuard(None,1.777749)
    result=new_job("CALM_VOF_SHARP_SEALED_PLUS_MINUS_5",opts,protection=guard,
        macro_source=P/"NIGHT_FLAP_20261104/VOF_MESH/MiniVofStokes.java",mpi_cpu_indices=CPUS)
    run=Path(result["checkpoint"]).parent
    dest=O/"CALM_VOF_SHARP_SEALED_PLUS_MINUS_5"
    dest.mkdir()
    for name in ("FINAL.sim","history.csv","gauges.csv","PRESSURE_BELOW_VAPOR.csv","DAY_RESULT.json",
                 "SOLVE_STATUS.json","RESIDUAL_FINAL25.json","LATEST_CHECKPOINT.json","step_wall.csv"):
        if (run/name).is_file():
            archive(run/name,dest/name)
    return dict(result,archive=str(dest),classification="EXPLORATORY_FROM_NONSTABILIZED_CALM")


if __name__=="__main__":
    if STOP.exists() or filtered_query(OWNER):
        raise RuntimeError("Existing STOP or occupied Mini port")
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        O.mkdir()
        for item in jobs:
            if STOP.exists() or filtered_query(OWNER):
                break
            label=item[0]
            update(stage=label)
            try:
                state["jobs"][label]=launch_snapshot(item)
            except Exception as err:
                state["jobs"][label]={"status":"HOLD","reason":str(err)}
            update()
        if not STOP.exists() and not filtered_query(OWNER):
            update(stage="CALM_VOF_SHARP_SEALED_PLUS_MINUS_5")
            try:
                state["jobs"][state["stage"]]=vof()
            except Exception as err:
                state["jobs"][state["stage"]]={"status":"HOLD","reason":str(err)}
        update(status="REVIEW",stage=None)
    finally:
        if not filtered_query(OWNER):
            LOCK.unlink()

