from pathlib import Path
import csv
import json
import os
import shutil
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_active_resume_1064 import GuardResume, coex, HERE, LOCK, STOP, new_job, sha, topology

ROOT=D.parents[2]
OUT=D/"matched_gap"
A=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104")


def history(path):
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def main():
    output=OUT/"RESULT.json"
    state=json.loads((HERE/"DAY_STATUS.json").read_text())
    ref=json.loads((A/"SHARP_SEALED_CYCLE_RESUME_1P064S/RESULT.json").read_text())
    geom=ROOT/"SEALED_OUTER_MESH_GAPPED"
    gap=json.loads((geom/"RESULT.json").read_text())["BASELINE"]
    mesh=json.loads((geom/"MESH_AUDIT.json").read_text())
    source=Path(gap["checkpoint"])
    if (output.exists() or STOP.exists() or not ref["full_cycle"] or ref["dt_s"]!=.00025
        or state["solver_state"]!="STOPPED" or state["stage"]!="MATCHED_FIXED_SHARP_SEALED_ACTIVE_RESUME_1064"
        or gap["status"]!="GAP_BASELINE_READY" or sha(source)!=gap["checkpoint_sha256"]):
        raise RuntimeError("Matched gap checkpoint or comparison reference mismatch")
    cpus=ref["cpu_indices"]
    topo=topology()
    p_class=max(x["efficiency_class"] for x in topo)
    if cpus!=[12,22] or not all(any(x["logical_cpu"]==cpu and x["group"]==0 and x["efficiency_class"]==p_class
                                    for x in topo) for cpu in cpus):
        raise RuntimeError("Prior Mini P-core binding no longer matches the host")
    coex.MASK=sum(1<<cpu for cpu in cpus)
    guard=GuardResume(None,1.777749)
    guard.watch=OUT/"W06_WATCH.csv"
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\n")
        guard.preflight()
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),cpu_indices=cpus,dt_s=.00025))
        result=new_job("MATCHED_FIXED_GAP_STABILIZE_THEN_ACTIVE",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,
            flow_cycle=True,expected_cells=mesh["cells"],expected_time=0,
            amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.00025,steps=800,
            fixed_protocol=True,fixed_cap_s=1.5,seeded_single_phase=True,gapped_geometry=True,
            after_fixed_motion=True,limit_seconds=12500),
            protection=guard,macro_source=OUT/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        fixed=case/"FIXED_PROTOCOL.json"
        result["fixed"]=json.loads(fixed.read_text()) if fixed.exists() else None
        rows=[r for r in history(case/"single_phase.csv") if "delta_measured_deg" in r]
        if rows:
            angles=[float(r["delta_measured_deg"]) for r in rows]
            result["angle_range_deg"]=[min(angles),max(angles)]
            result["max_CFL"]=max(float(r["max_CFL"]) for r in rows)
            result["min_flap_vapor_margin_kPa"]=min(float(r["flap_vapor_margin_Pa"]) for r in rows)/1000
            result["full_cycle"]=(result["status"]=="PASS_DIAGNOSTIC_SMOKE" and result["transport_ok"]
                and len(rows)==800 and min(angles)<-1.99 and max(angles)>1.99 and abs(angles[-1])<.01)
        else:
            result["full_cycle"]=False
        result["W06"]=dict(peak=guard.peak,stop=guard.stopped,slowdown_gate_enabled=False)
        coex.save(output,result)
        dest=A/"GAP_MATCHED_STABILIZE_THEN_ACTIVE"
        dest.mkdir(exist_ok=False)
        files=(Path(result["checkpoint"]),case/"single_phase.csv",case/"fixed_history.csv",
               case/"fixed_windows.csv",case/"residual_per_step.csv",fixed,output)
        for file in files:
            if not file.exists():
                continue
            target=dest/file.name
            shutil.copy2(file,target)
            if sha(file)!=sha(target):
                raise RuntimeError(f"Archive verification failed for {file.name}")
        sys.path.insert(0,str(D.parents[1]))
        from plot_results import plot
        plot()
        for name in ("full_histories_EN.png","CL_CD_vs_deflection_EN.png"):
            file=D.parents[1]/name
            if file.exists():
                shutil.copy2(file,dest/name)
    except Exception as exc:
        if not output.exists() or json.loads(output.read_text())["status"]=="RUNNING":
            coex.save(output,dict(status="HOLD",error=str(exc)))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

