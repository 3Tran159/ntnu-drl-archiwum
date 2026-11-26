from pathlib import Path
import json
import os
import shutil
import sys
import csv

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_active_resume_1064 import GuardResume, coex, HERE, LOCK, STOP, new_job, sha

ROOT=D.parents[2]
OUT=D/"matched_gap_resume0600"
A=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104")


def main():
    output=OUT/"RESULT.json"
    original=json.loads((D/"matched_gap"/"RESULT.json").read_text())
    state=json.loads((HERE/"DAY_STATUS.json").read_text())
    prefix=Path(state["output"])
    receipt=json.loads((prefix/"LATEST_CHECKPOINT.json").read_text())
    source=Path(receipt["path"])
    if (output.exists() or STOP.exists() or original["status"]!="HOLD" or state["solver_state"]!="STOPPED"
        or state["stage"]!="MATCHED_FIXED_GAP_STABILIZE_THEN_ACTIVE"
        or not receipt["complete_write"] or abs(receipt["time_s"]-.6)>1e-9
        or source.parent!=prefix or source.stat().st_size!=receipt["bytes"]
        or "Connection reset" not in (prefix/"client.log").read_text(encoding="utf8",errors="replace")):
        raise RuntimeError("Gap transport recovery preflight blocked")
    digest=sha(source)
    target=A/"GAP_FIXED_CHECKPOINT_0P600S.sim"
    if not target.exists():
        shutil.copy2(source,target)
    if sha(target)!=digest:
        raise RuntimeError("Gap restart archive hash mismatch")
    cpus=[12,22]
    coex.MASK=sum(1<<cpu for cpu in cpus)
    guard=GuardResume(None,1.777749)
    guard.watch=OUT/"W06_WATCH.csv"
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\n")
        guard.preflight()
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),input_sha256=digest,
                             restart_time_s=.6,recovery_number=1))
        result=new_job("MATCHED_FIXED_GAP_RESUME0600_STABILIZE_THEN_ACTIVE",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,
            flow_cycle=True,expected_cells=19502,expected_time=.6,
            amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.00025,steps=800,
            fixed_protocol=True,fixed_cap_s=1.5,seeded_single_phase=True,gapped_geometry=True,
            fixed_from_unsteady=True,restore_fixed_history=True,fixed_prefix_directory=prefix.as_posix(),
            after_fixed_motion=True,limit_seconds=12500),
            protection=guard,macro_source=OUT/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        result["fixed"]=json.loads((case/"FIXED_PROTOCOL.json").read_text())
        with (case/"single_phase.csv").open() as stream:
            rows=[r for r in csv.DictReader(stream) if "delta_measured_deg" in r]
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
        dest=A/"GAP_MATCHED_STABILIZE_THEN_ACTIVE_RESUME0600"
        dest.mkdir(exist_ok=False)
        for name in ("FINAL.sim","single_phase.csv","fixed_history.csv","fixed_windows.csv",
                     "residual_per_step.csv","FIXED_PROTOCOL.json"):
            file=case/name
            if file.exists():
                shutil.copy2(file,dest/name)
                if sha(file)!=sha(dest/name):
                    raise RuntimeError("Archive verification failed: "+name)
        shutil.copy2(output,dest/"RESULT.json")
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

