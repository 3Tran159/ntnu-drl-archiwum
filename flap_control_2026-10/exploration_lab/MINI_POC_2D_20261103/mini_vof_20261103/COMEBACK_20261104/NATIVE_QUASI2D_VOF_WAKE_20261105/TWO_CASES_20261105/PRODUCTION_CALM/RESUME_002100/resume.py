from pathlib import Path
import csv,math,os,sys
D=Path(__file__).resolve().parent
P=D.parents[3]
sys.path.insert(0,str(P/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"))
import run as c

FIXED="CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE"
MOTION="CALM_VOF_NATIVE_FULL_BAND_ACTIVE_PLUS_MINUS_5"
START=P/"runs"/(FIXED+"_20261105_140934")
SOURCE_SHA="510b683925285244b30d15a41e3e472e359036cb7f1a3ecb69f3c6bb58c3c8c4"
DT=.0002
CPUS=[22,23]
W=250

def checkpoint(run):
    r=c.read(run/"LATEST_CHECKPOINT.json")
    path=Path(r["path"])
    if not r["complete_write"] or path.parent!=run or path.stat().st_size!=r["bytes"]:
        raise RuntimeError("Native checkpoint receipt invalid")
    return r["time_s"],path,r["step_in_job"]

def transport_failure(run):
    log=(run/"client.log").read_text(encoding="utf-8",errors="replace")
    return "Connection reset" in log and "DisconnectedException" in log and not (run/"SOLVE_STATUS.json").exists()

def saved_rows(run,step,t):
    rows=c.tail(run/"history.csv")[:step]
    if (len(rows)!=step or abs(float(rows[-1]["time_s"])-t)>1e-9 or
        any(abs(float(r[k]))>1e-10 for r in rows for k in ("delta_measured_deg","delta_command_deg"))):
        raise RuntimeError("Checkpoint and fixed history are inconsistent")
    return rows

def launch():
    day=c.read(P/"DAY_STATUS.json")
    if Path(day["output"])!=START or day["solver_state"]!="STOPPED" or c.STOP.exists() or c.LOCK.exists() or c.filtered_query(c.OWNER):
        raise RuntimeError("Expected stopped native CALM case")
    time_s,source,used=checkpoint(START)
    if abs(time_s-.021)>1e-9 or c.sha(source).lower()!=SOURCE_SHA or not transport_failure(START):
        raise RuntimeError("Restart source or transport failure did not verify")
    initial=c.read(START/"AF_RESUME_HISTORY.json")
    source_history=Path(initial["path"])
    rows=saved_rows(START,used,time_s)
    stable=0
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=dict(status="RUNNING",stage=FIXED,source=str(source),start_s=time_s,motion_authorized=False,
        checkpoint_sha256=c.sha(source),checkpoint_interval_s=.005,cpu_indices=CPUS)
    def status(**changes):
        c.status(state,**changes)
        c.coex.save(D/"STATUS.json",state)
    try:
        mask=sum(1<<cpu for cpu in CPUS)
        c.local.night_flap.MASK=mask
        c.coex.MASK=mask
        settings=dict(stokes=True,foil=True,expected_cells=25617,calm_only=True,clean_calm=True,
                      matched_calm=True,pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,
                      dt=DT,inner=20,save_interval_s=.005,af_native=True)
        def job(stage,**options):
            return c.new_job(stage,{**settings,**options},protection=c.NightGuard(None,1.777749),
                macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
        for attempt in range(2):
            seed_rows=rows[-(W+used%W):]
            for i,r in enumerate(seed_rows):
                if (not all(math.isfinite(float(r[k])) for k in ("CL","CD")) or
                    abs(float(r["time_s"])-(time_s-(len(seed_rows)-1-i)*DT))>1e-9):
                    raise RuntimeError("Force seed time mismatch")
            seed=D/f"FIXED_SEED_{attempt+1}.csv"
            with seed.open("x",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=("time_s","CL","CD"),extrasaction="ignore")
                writer.writeheader()
                writer.writerows(seed_rows)
            status(operation="RESUMING_FIXED",source=str(source),start_s=time_s,checkpoint_sha256=c.sha(source),
                completed_fixed_steps=used,seeded_samples=len(seed_rows),transport_retry=attempt)
            try:
                fixed=job(FIXED,source=source,expected_time=time_s,source_af_history=source_history.as_posix(),
                    af_branch_history=True,matched_calm_fixed=True,moving=False,steps=6000-used,
                    fixed_elapsed_before=used,fixed_window_seed=seed.as_posix(),fixed_stable_count=stable,
                    limit_seconds=21600)
                break
            except Exception:
                day=c.read(P/"DAY_STATUS.json")
                failed=Path(day["output"])
                if (attempt!=0 or failed==START or day["solver_state"]!="STOPPED" or c.STOP.exists()
                    or c.filtered_query(c.OWNER) or not transport_failure(failed)):
                    raise
                saved,cp,step=checkpoint(failed)
                if step<25 or saved<=time_s:
                    raise
                rows.extend(saved_rows(failed,step,saved))
                used+=step
                time_s,source=saved,cp
                source_history=Path(c.read(failed/"AF_RESUME_HISTORY.json")["path"])
                path=failed/"CALM_FIXED_PROGRESS.json"
                if path.exists():
                    gate=c.read(path)
                    if gate["time_s"]<=saved+1e-9:
                        stable=gate["stable_windows"]
        fixed_copy=c.publish(fixed)
        state["fixed_result"]=fixed
        gate=fixed.get("stabilization",{})
        valid=(fixed["status"]=="PASS_CALM_FORCE_STABILIZATION" and fixed["transport_ok"] and
             gate.get("stable_windows")==3 and gate["CL_drift_fraction"]<.005 and gate["CD_drift_fraction"]<.005 and
             abs(gate["time_s"]-fixed["state"]["time_s"])<1e-9 and
             c.sha(fixed_copy/"FINAL.sim")==fixed["checkpoint_sha256"])
        if not valid or c.STOP.exists():
            status(status="HOLD",operation="FIXED_GATE_NOT_PASSED",stage=None)
            return
        fixed_run=Path(fixed["checkpoint"]).parent
        last=c.tail(fixed_run/"history.csv")[-1]
        if any(abs(float(last[k]))>1e-10 for k in ("delta_measured_deg","delta_command_deg")):
            raise RuntimeError("Fixed gate source angle is not zero")
        status(stage=MOTION,motion_authorized=True,operation="STARTING_MOTION",stable_checkpoint=fixed["checkpoint"])
        active=job(MOTION,source=Path(fixed["checkpoint"]),expected_time=gate["time_s"],
            source_af_history=Path(c.read(fixed_run/"AF_RESUME_HISTORY.json")["path"]).as_posix(),
            moving=True,flow_cycle=True,calm_active_pilot=True,flap_cycle_deg=5,flap_quarter_s=.125,
            steps=2500,limit_seconds=18000)
        c.publish(active)
        status(status="REVIEW",stage=None,operation="MOTION_FINISHED",motion_result=active)
    except Exception as err:
        status(status="HOLD",operation="NATIVE_VOF_INTERRUPTED",reason=str(err))
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()

if __name__=="__main__":
    launch()

