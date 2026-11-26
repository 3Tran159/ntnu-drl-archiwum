from pathlib import Path
import csv
import datetime as dt
import os
import time

from night_flap import (CPUS, END, HERE, LOCK, OUT, OWNER, STATUS, STOP, VP,
                        NightGuard, archive, await_resources, coex, history,
                        new_job, query, read, sha)
from calm_pair_ready import run_vof_pair

STAGE="GAP_PLUS_MINUS_5_DT020_RESUME"


def gap_retry(state):
    prior=state["runs"]["GAP_PLUS_MINUS_5"]
    run=Path(prior["checkpoint"]).parent
    fields,rows=history(run/"single_phase.csv")
    final=rows[-1]
    if prior["status"]!="HOLD_SINGLE_PHASE_SAFETY" or not (25 < float(final["max_CFL"]) < 25.1):
        raise RuntimeError("CFL-only retry conditions not satisfied")
    if not (float(final["mass_relative"])<=1e-4 and float(final["volume_min"])>0
            and float(final["face_validity"])>=.5 and float(final["quality"])>0
            and float(final["k_min"])>1.0001e-10 and float(final["omega_min"])>1.0001e-10
            and float(final["mut_mu_max"])<99999
            and abs(float(final["delta_command_deg"])-float(final["delta_measured_deg"]))<.08):
        raise RuntimeError("Gap also violated another solver safety check")
    checkpoint=run/"ACTIVE_STEP0400.sim"
    if not await_resources(state,STAGE) or END-time.time()<420:
        return {"status":"HOLD_RESOURCE_OR_DEADLINE"}
    dest=OUT/STAGE
    dest.mkdir()
    source=dest/"INPUT_T1P100.sim"
    archive(checkpoint,source)
    kept=rows[:400]
    if abs(float(kept[-1]["time_s"])-1.1)>1e-9 or float(kept[-1]["max_CFL"])>25:
        raise RuntimeError("Prior saved checkpoint time or CFL verification failed")
    state.update(status="RUNNING",active=STAGE)
    coex.save(STATUS,state)
    opts=dict(source=source,expected_time=1.1,resume_coarse_active=True,motion_origin_s=1.,
        reference_tip_x_m=1.19,reference_tip_y_m=0.,stokes=True,foil=True,moving=True,
        single_phase=True,coarse_2d_active=True,flow_cycle=True,expected_cells=19502,amplitude=0,
        old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.0002,steps=2000,seeded_single_phase=True,
        gapped_geometry=True,fixed_from_unsteady=True,pressure_diagnostic_only=True,
        flap_cycle_deg=5,flap_quarter_s=.125,limit_seconds=min(11000,int(END-time.time()-90)))
    result=new_job(STAGE,opts,protection=NightGuard(None,1.777749),macro_source=HERE/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
    latest=Path(result["checkpoint"]).parent
    header,tail=history(latest/"single_phase.csv")
    if header!=fields or any(abs(float(row["time_s"])-(1.1+i*.0002))>1e-8 for i,row in enumerate(tail,1)):
        raise RuntimeError("Retry history does not match checkpoint")
    for name in ("FINAL.sim","LATEST_CHECKPOINT.json","single_phase.csv","residual_per_step.csv","PRESSURE_BELOW_VAPOR.csv","SOLVE_STATUS.json"):
        if (latest/name).is_file():
            archive(latest/name,dest/name)
    combined=kept+tail
    with (dest/"cycle_full_available.csv").open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(combined)
    angles=[float(row["delta_measured_deg"]) for row in combined]
    result.update(archive=str(dest),total_steps=len(combined),angle_range_deg=[min(angles),max(angles)],
        flap_pmin_Pa=min(float(r["pflap_min_Pa"]) for r in combined),
        hinge_pmin_Pa=min(float(r["pgap_min_Pa"]) for r in combined),
        samples_at_or_below_vapor=sum(min(float(r["pflap_min_Pa"]),float(r["pgap_min_Pa"]))<=VP for r in combined),
        cycle_complete=(result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
            and len(tail)==2000 and min(angles)<-4.99 and max(angles)>4.99 and abs(angles[-1])<.01),
        initial_dt_s=.00025,change_dt_at_s=1.1,training_approved=False)
    coex.save(dest/"RESULT.json",result)
    return result


def main():
    if STOP.exists() or query(OWNER):
        raise RuntimeError("Existing controller or manual STOP")
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=read(STATUS)
    try:
        if state["status"]!="REVIEW" or any(state["runs"].get(name,{}).get("reason")!="Invalid wall mesh override"
            for name in ("CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP")):
            raise RuntimeError("Native staging retry does not match previous preflight failures")
        archive(STATUS,OUT/("BEFORE_MESH_STAGING_RETRY_"+dt.datetime.now().strftime("%H%M%S")+".json"))
        state["native_import_retry"]="Matched inputs moved to launcher-approved directory with unchanged hashes"
        run_vof_pair(state,max_budget_seconds=5600)
        coex.save(STATUS,state)
        if not STOP.exists() and not query(OWNER) and END-time.time()>=420:
            try:
                state["runs"][STAGE]=gap_retry(state)
            except Exception as exc:
                state["runs"][STAGE]={"status":"HOLD","reason":str(exc)}
        state["status"]="STOPPED" if STOP.exists() else "REVIEW"
    except Exception as exc:
        state.update(status="HOLD",reason=str(exc))
        raise
    finally:
        state["active"]=None
        coex.save(STATUS,state)
        if not query(OWNER):
            LOCK.unlink()

if __name__=="__main__":
    main()

