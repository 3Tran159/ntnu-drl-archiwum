from pathlib import Path
import csv
import json
import os
import shutil
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from run_without_w06_slowdown_stop import GuardP, coex, HERE, LOCK, STOP, new_job, running_w06, sha, topology

A=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104")
META=A/"SHARP_SEALED_ACTIVE_PAUSE_1P064S_RESUME.json"
OUT=D/"active_resume_1064"


class GuardResume(GuardP):
    def observe_w06(self):
        jobs=running_w06()
        if len(jobs)!=1 or jobs[0][1]!=1:
            return
        if self.folder!=jobs[0][0]:
            self.folder=jobs[0][0]
            self.last_sample=None
        super().observe_w06()


def history(path):
    with path.open(newline="") as stream:
        r=csv.DictReader(stream)
        return r.fieldnames,list(r)


def main():
    output=OUT/"RESULT.json"
    settings=json.loads(META.read_text(encoding="utf-8-sig"))
    state=json.loads((HERE/"DAY_STATUS.json").read_text())
    original=json.loads((D/"active_1050"/"RESULT.json").read_text())
    marker="User requested Mini checkpoint before Windows shutdown."
    source=Path(settings["checkpoint"])
    prev=Path(settings["history"])
    if (output.exists() or not STOP.exists() or STOP.read_text().strip()!=marker
        or settings["status"]!="PAUSED_USER_SHUTDOWN" or state["solver_state"]!="STOPPED"
        or state["stage"]!="MATCHED_FIXED_SHARP_SEALED_ACTIVE_1050"
        or not original["transport_ok"] or sha(source)!=settings["sha256"]
        or original["checkpoint_sha256"]!=settings["sha256"]
        or not prev.is_file() or prev.parent!=Path(state["output"])):
        raise RuntimeError("Paused active flap checkpoint or controller identity mismatch")
    fields,prefix=history(prev)
    start=settings["physical_time_s"]
    dt=settings["dt_s"]
    if (len(prefix)!=settings["completed_cycle_steps"] or len(prefix)+settings["remaining_cycle_steps"]!=800
        or abs(float(prefix[-1]["time_s"])-start)>1e-9
        or abs(start+settings["remaining_cycle_steps"]*dt-settings["cycle_end_s"])>1e-9):
        raise RuntimeError("Paused active flap history does not match checkpoint")
    cpus=settings["logical_cpu"]
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
        archived=OUT/"STOP_REQUESTED_SHUTDOWN_ARCHIVED.txt"
        if archived.exists() or STOP.read_text().strip()!=marker:
            raise RuntimeError("Unexpected Mini shutdown marker")
        STOP.rename(archived)
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),start_s=start,
                  end_s=settings["cycle_end_s"],previous_steps=len(prefix),cpu_indices=cpus))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_ACTIVE_RESUME_1064",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,resume_coarse_active=True,flow_cycle=True,expected_cells=17462,
            expected_time=start,motion_origin_s=settings["cycle_origin_s"],
            reference_tip_x_m=settings["reference_tip_x_m"],reference_tip_y_m=settings["reference_tip_y_m"],
            amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=dt,
            steps=settings["remaining_cycle_steps"],limit_seconds=6300),
            protection=guard,macro_source=D/"active_1050"/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        current,tail=history(case/"single_phase.csv")
        rows=prefix+tail
        if fields!=current or any(abs(float(row["time_s"])-(1.05+dt*i))>1e-8 for i,row in enumerate(rows,1)):
            raise RuntimeError("Active cycle history is discontinuous at resume")
        with (case/"single_phase_combined.csv").open("x",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        shutil.copy2(A/"SHARP_SEALED_FIXED_STABLE_HISTORY.csv",case/"fixed_history.csv")
        angles=[float(row["delta_measured_deg"]) for row in rows]
        result["combined_steps"]=len(rows)
        result["angle_range_deg"]=[min(angles),max(angles)]
        result["min_flap_vapor_margin_kPa"]=min(float(row["flap_vapor_margin_Pa"]) for row in rows)/1000
        result["max_CFL"]=max(float(row["max_CFL"]) for row in rows)
        result["full_cycle"]=(result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
            and len(rows)==800 and min(angles)<-1.99 and max(angles)>1.99 and abs(angles[-1])<.01)
        result["W06"]=dict(peak=guard.peak,stop=guard.stopped,slowdown_gate_enabled=False)
        result["cpu_indices"]=cpus
        coex.save(output,result)
        dest=A/"SHARP_SEALED_CYCLE_RESUME_1P064S"
        dest.mkdir(exist_ok=False)
        for file in (Path(result["checkpoint"]),case/"single_phase_combined.csv",case/"fixed_history.csv",
                     case/"residual_per_step.csv",output):
            target=dest/file.name
            shutil.copy2(file,target)
            if sha(file)!=sha(target):
                raise RuntimeError(f"Archive verification failed for {file.name}")
        sys.path.insert(0,str(D.parents[1]))
        from plot_results import plot
        plot()
    except Exception as exc:
        if not output.exists() or json.loads(output.read_text())["status"]=="RUNNING":
            coex.save(output,dict(status="HOLD",error=str(exc)))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

