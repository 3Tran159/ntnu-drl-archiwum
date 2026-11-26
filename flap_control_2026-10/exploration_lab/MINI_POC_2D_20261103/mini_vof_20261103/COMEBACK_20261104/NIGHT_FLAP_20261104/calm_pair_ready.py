import math
from pathlib import Path
import statistics
import time

from night_flap import (CPUS, END, HERE, OUT, OWNER, STOP, VP, NightGuard,
                        archive, await_resources, coex, history, new_job, query, read, sha)

D = HERE / "VOF_MESH"
DSTEP = .00025
COMMON = dict(stokes=True,foil=True,calm_only=True,clean_calm=True,matched_calm=True,
              pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,dt=DSTEP,inner=20,
              save_interval_s=.05,pressure_urf=.5,pressure_tol=.01)


def run(stage, options, budget_seconds=9800):
    if STOP.exists() or query(OWNER) or END-time.time()<420 or budget_seconds<420:
        return {"status":"HOLD_RESOURCE_OR_DEADLINE"}
    guard = NightGuard(None,1.777749)
    value=new_job(stage,dict(COMMON,**options,limit_seconds=min(budget_seconds,int(END-time.time()-90))),
                  protection=guard,macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
    src=Path(value["checkpoint"]).parent
    dest=OUT/stage
    dest.mkdir()
    for name in ("FINAL.sim","LATEST_CHECKPOINT.json","history.csv","gauges.csv","gauges_absorption.csv",
                 "SETUP_READBACK.json","CALM_HYDROSTATIC_AUDIT.json","CLEAN_NATIVE_INITIALIZATION.json",
                 "CALM_FIXED_PROGRESS.json","PRESSURE_BELOW_VAPOR.csv","RESIDUAL_FINAL25.json",
                 "residual_per_step.csv","SOLVE_STATUS.json","step_wall.csv","wall_yplus_pressure.csv"):
        if (src/name).is_file():
            archive(src/name,dest/name)
    _,rows=history(dest/"history.csv")
    value.update(archive=str(dest),training_approved=False,data_class="EXPLORATORY")
    if rows:
        value.update(pflap_min_Pa=min(float(r["pflap"]) for r in rows),
                     samples_flap_below_vapor=sum(float(r["pflap"])<=VP for r in rows),
                     max_interface_CFL=max(float(r["interface_CFL"]) for r in rows))
        last=rows[-round(.05/DSTEP):]
        if len(last)==round(.05/DSTEP):
            value["last_0p05_s"]={
                "CL_buoyancy_corrected":statistics.mean(float(r["CL"]) for r in last),
                "CL_total":statistics.mean(float(r["Fz"])/3855.6 for r in last),
                "CD":statistics.mean(float(r["CD"]) for r in last),
                 "mean_Mh_Nm_per_m":statistics.mean(float(r["Mh_per_m"]) for r in last),
                "pABS_flap_min_Pa":min(float(r["pflap"]) for r in last)}
    if (dest/"CALM_FIXED_PROGRESS.json").exists():
        value["stabilization"]=read(dest/"CALM_FIXED_PROGRESS.json")
    coex.save(dest/"RESULT.json",value)
    return value


def pilot_data(result,mesh):
    dest=Path(result["archive"])
    import csv
    _,rows=history(dest/"history.csv")
    with (dest/"trajectory_EXPLORATORY.csv").open("x",newline="") as f:
        keys=("run_id","mesh_id","physical_time_s","wave_phase_rad","eta_at_foil_m",
              "Ux_m_s","Uy_m_s","delta_deg","delta_dot_rad_s","CL","CD","Fx_N","Fz_N",
              "Mh_Nm_per_m","pABS_flap_Pa","CFL","hinge_power_fluid_W","numeric_status")
        writer=csv.writer(f);writer.writerow(keys)
        _,gauges=history(dest/"gauges.csv")
        eta={row["time_s"]:row["eta_actual_m"] for row in gauges if abs(float(row["x_m"])-.952)<1e-10}
        for row in rows:
            writer.writerow((dest.name,mesh["sha256"],row["time_s"],"",eta.get(row["time_s"],""),
                 row["Ux"],row["Uy"],row["delta_measured_deg"],row["delta_dot_rad_s"],row["CL"],row["CD"],
                 row["Fx"],row["Fz"],row["Mh_per_m"],row["pflap"],row["max_CFL"],
                 row["hinge_power_fluid_W"],"EXPLORATORY"))
    coex.save(dest/"TRAJECTORY_METADATA.json",dict(status="EXPLORATORY",wave="none",training_approved=False,
         geometry="sharp sealed",span_m=.02,velocity_m_s=18,pressure_vapor_Pa=VP,
         lift="Fz positive upward; CL buoyancy corrected using displaced volume",
         drag="Fx positive downstream; CD normalized by 0.5*rho*U^2*c*span",
         motion="positive trailing-edge down; signed hinge power is from fluid torque",
         numeric_status=result["status"]))


def run_vof_pair(state,max_budget_seconds=9800,suffix=""):
    pair=read(D/"PAIR.json")
    budget=max(0,int((END-time.time()-600)/2))
    state["calm_equal_budget_seconds"]=min(max_budget_seconds,budget)
    for key in ("sealed","gap"):
        stage="CALM_VOF_FIXED_"+key.upper()+suffix
        state.update(status="RUNNING",active=stage)
        coex.save(HERE/"STATUS.json",state)
        if not await_resources(state,stage):
            state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
            continue
        state.pop("resource_wait",None)
        mesh=pair[key]
        path=Path(mesh["path"])
        try:
            if sha(path)!=mesh["sha256"] or mesh["minimum_original_volume_m3"]<=0:
                raise RuntimeError("Prepared mesh checksum/volume mismatch")
            state["runs"][stage]=run(stage,dict(fresh=True,mesh_override=path.as_posix(),
                mesh_override_sha256=mesh["sha256"],expected_cells=mesh["cells"],steps=5200,
                matched_calm_fixed=True), budget_seconds=min(max_budget_seconds,budget))
        except Exception as exc:
            state["runs"][stage]={"status":"HOLD","reason":str(exc)}
        coex.save(HERE/"STATUS.json",state)
    sealed=state["runs"]["CALM_VOF_FIXED_SEALED"+suffix]
    gap=state["runs"]["CALM_VOF_FIXED_GAP"+suffix]
    state["runs"]["CALM_VOF_PAIR"+suffix]={"status":"PASS_FORCE_STABILIZATION" if
        all(x["status"]=="PASS_CALM_FORCE_STABILIZATION" and x["transport_ok"] for x in (sealed,gap)) else "HOLD"}
    stage="SURROGATE_PILOT"+suffix
    if state["runs"]["CALM_VOF_PAIR"+suffix]["status"]!="PASS_FORCE_STABILIZATION":
        state["runs"][stage]={"status":"HOLD","reason":"Matched CALM/VOf fixed force gates not both passed"}
        return
    if any(x["last_0p05_s"]["pABS_flap_min_Pa"]<=VP for x in (sealed,gap)):
        state["runs"][stage]={"status":"HOLD","reason":"A stabilized fixed analysis window crossed vapor pressure"}
        return
    if not await_resources(state,stage):
        state["runs"][stage]={"status":"HOLD_RESOURCE_OR_DEADLINE"}
        return
    state.pop("resource_wait",None)
    state["active"]=stage
    coex.save(HERE/"STATUS.json",state)
    source=Path(sealed["archive"])/"FINAL.sim"
    if sha(source)!=sealed["checkpoint_sha256"]:
        raise RuntimeError("Pilot input checksum mismatch")
    try:
        result=run(stage,dict(source=source,expected_time=sealed["state"]["time_s"],
            expected_cells=pair["sealed"]["cells"],steps=round(.2/DSTEP),moving=True,flow_cycle=True,
            calm_active_pilot=True))
        state["runs"][stage]=result
        if "archive" in result:
            pilot_data(result,pair["sealed"])
    except Exception as exc:
        state["runs"][stage]={"status":"HOLD","reason":str(exc)}


