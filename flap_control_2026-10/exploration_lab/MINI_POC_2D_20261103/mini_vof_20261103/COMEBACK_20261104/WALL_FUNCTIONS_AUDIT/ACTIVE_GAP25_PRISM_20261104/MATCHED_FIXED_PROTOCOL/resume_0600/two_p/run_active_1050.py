from pathlib import Path
import csv
import json
import os
import shutil
import sys
import time

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_without_w06_slowdown_stop import GuardP, coex, HERE, LOCK, STOP, new_job, running_w06, sha

ARCHIVE=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104")
SOURCE=ARCHIVE/"SHARP_SEALED_FIXED_STABLE_1P050S.sim"
OUT=D/"active_1050"

def main():
    result_file=OUT/"RESULT.json"
    old=json.loads((D/"FIXED_EXTENSION_RESULT.json").read_text())
    state=json.loads((HERE/"DAY_STATUS.json").read_text())
    if (result_file.exists() or STOP.exists() or old["status"]!="PASS_FIXED_STABILIZATION"
        or state["solver_state"]!="STOPPED" or state["operation"]!="PASS_FIXED_STABILIZATION"
        or sha(SOURCE)!=old["checkpoint_sha256"] or abs(old["state"]["time_s"]-1.05)>1e-9):
        raise RuntimeError("Sharp sealed cycle checkpoint or controller identity mismatch")
    cpus=old["cpu_indices"]
    if cpus!=[12,22]:
        raise RuntimeError("Unexpected prior P-core binding")
    jobs=running_w06()
    if len(jobs)!=1 or jobs[0][1]!=1:
        raise RuntimeError("Expected the measured one-rank W06 job")
    guard=GuardP(jobs[0][0],old["W06"]["baseline_s"])
    guard.watch=OUT/"W06_WATCH.csv"
    coex.MASK=sum(1<<cpu for cpu in cpus)
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\n")
        guard.preflight()
        coex.save(result_file,dict(status="RUNNING",checkpoint_source=str(SOURCE),
                  start_s=1.05,end_s=1.25,cpu_indices=cpus,mpi_ranks=2))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_ACTIVE_1050",dict(
            source=SOURCE,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=17462,expected_time=1.05,
            motion_origin_s=1.05,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,
            dt=.00025,steps=800,seeded_single_phase=True,fixed_from_unsteady=True,
            limit_seconds=2300),protection=guard,macro_source=OUT/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        with (case/"single_phase.csv").open() as f:
            rows=list(csv.DictReader(f))
        if rows:
            angles=[float(row["delta_measured_deg"]) for row in rows]
            result["angle_range_deg"]=[min(angles),max(angles)]
            result["min_flap_vapor_margin_kPa"]=min(float(row["flap_vapor_margin_Pa"]) for row in rows)/1000
            result["max_CFL"]=max(float(row["max_CFL"]) for row in rows)
            result["full_cycle"]=(result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
                and len(rows)==800 and min(angles)<-1.99 and max(angles)>1.99 and abs(angles[-1])<.01)
        result["W06"]=dict(peak=guard.peak,stop=guard.stopped,slowdown_gate_enabled=False)
        result["cpu_indices"]=cpus
        coex.save(result_file,result)
        shutil.copy2(ARCHIVE/"SHARP_SEALED_FIXED_STABLE_HISTORY.csv",case/"fixed_history.csv")
        sys.path.insert(0,str(D.parents[1]))
        from plot_results import plot
        plot()
        dest=ARCHIVE/"SHARP_SEALED_CYCLE_FROM_1P050S"
        dest.mkdir(exist_ok=False)
        for f in (Path(result["checkpoint"]),case/"single_phase.csv",case/"fixed_history.csv",
                  case/"residual_per_step.csv",result_file):
            target=dest/f.name
            shutil.copy2(f,target)
            if sha(f)!=sha(target):
                raise RuntimeError(f"Archive verification failed for {f.name}")
    except Exception as exc:
        if not result_file.exists() or json.loads(result_file.read_text())["status"]=="RUNNING":
            coex.save(result_file,dict(status="HOLD",error=str(exc)))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

