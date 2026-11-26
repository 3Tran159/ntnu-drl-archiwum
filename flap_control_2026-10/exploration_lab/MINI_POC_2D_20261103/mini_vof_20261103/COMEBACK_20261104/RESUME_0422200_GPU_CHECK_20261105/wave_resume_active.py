"""Resume the approved moving STAR case only after native continuity readback."""
import csv
import math
import os
from pathlib import Path
import sys

import wave_phase_map_analysis as analysis
import wave_phase_map_campaign as campaign
from resume import CPUS, D, P, c, run_day
from wave_resume_mini_only import MiniGuard, mini_job

ACTIVE = "PHASE_MAP_WAVE_ACTIVE_I1DEG"
ORIGINAL = P / "runs/PHASE_MAP_WAVE_ACTIVE_I1DEG_20261106_153215"



def at_time(path, t, x=None):
    with path.open(newline="") as file:
        hits = [row for row in csv.DictReader(file)
                if abs(float(row["time_s"])-t)<1e-8 and
                (x is None or abs(float(row["x_m"])-x)<1e-7)]
    if len(hits)!=1:
        raise RuntimeError(f"Expected one checkpoint measurement in {path.name}")
    return hits[0]


def resume_job(stage, source, start, macro_source, **config):
    row=at_time(source.parent/"history.csv",start)
    gauge=at_time(source.parent/"gauges.csv",start,.952)
    setup=c.read(source.parent/"AF_VOF_PLAYBACK_SETUP.json")
    # Every copy continues the same history basename so existing STAR scenes remain linked.
    previous=source.parent/Path(setup["history"]).name
    if not previous.is_file():
        raise RuntimeError("Missing active STAR animation history")
    return mini_job(stage,source,start,macro_source,**{
        **config,
        "resume_angle_deg":float(row["delta_measured_deg"]),
        "resume_phase_rad":float(row["phase_analytic_at_foil_rad"]),
        "resume_eta_m":float(gauge["eta_actual_m"]),
        "source_active_playback":previous.as_posix(),
    })


def main(check):
    if c.LOCK.exists():
        raise RuntimeError("Another Mini controller owns the solver")
    MiniGuard().preflight()
    state=c.read(campaign.STATE)
    if state["operation"]!="PAUSED_VERIFIED" or not state["fixed_gate"]["passed"]:
        raise RuntimeError("Expected verified relocation pause after WAVE/FIXED")
    segment=state["segments"][-1]
    pause=c.read(D/"ACTIVE_RELOCATION_PAUSE_20261106.json")
    job=c.read(ORIGINAL/"job.json")
    origin=float(job["motion_origin_s"])
    period=float(job["encounter_period_s"])
    folder=Path(segment["folder"])
    saved_job=c.read(folder/"job.json")
    source,t,history,n=campaign.recover(folder,float(saved_job["expected_time"]),int(saved_job["steps"]))
    done=round((t-origin)/campaign.DT)
    if (segment["stage"]!=ACTIVE or Path(segment["checkpoint"])!=source
        or Path(pause["checkpoint"])!=source or c.sha(source)!=pause["sha256"]
        or abs(t-float(pause["physical_time_s"]))>1e-9 or done!=pause["active_step_offset"]
        or abs(t-origin-done*campaign.DT)>1e-8):
        raise RuntimeError("Unexpected relocation checkpoint")
    if any(c.sha(Path(row["checkpoint"]))!=row["sha256"] for row in state["segments"]):
        raise RuntimeError("Campaign checkpoint lineage changed")
    with (ORIGINAL/"vertices_0000.csv").open(newline="") as file:
        reader=csv.reader(file); next(reader)
        vertices=[(float(row[0]),float(row[1])) for row in reader if float(row[0])>=1.15]
    x,y=max(vertices,key=lambda v:math.hypot(v[0]-.952,v[1]-.02128173276777))
    options=dict(phase_identification=True,harmonic_flap_deg=1,encounter_period_s=period,
        motion_origin_s=origin,motion_ramp_s=float(job["motion_ramp_s"]),
        flow_cycle=False,af_branch_history=False,save_interval_s=.10,early_save_steps=0,
        resume_phase_active=True,resume_active_allowed=True,reference_tip_x_m=x,reference_tip_y_m=y)
    row=at_time(folder/"history.csv",t)
    phase=2*math.pi*.952/10-2*math.pi*t/period
    q=(t-origin)/options["motion_ramp_s"]
    target=q**3*(10-15*q+6*q*q)*math.sin(phase)
    if abs(target-float(row["delta_measured_deg"]))>1e-7 or abs(phase-float(row["phase_analytic_at_foil_rad"]))>1e-8:
        raise RuntimeError("Historical command, angle or phase mismatch")
    if check:
        print(f"Input verified: t={t:.6f} s, angle={target:.9f} deg, phase={phase:.9f} rad, zero-angle tip=({x},{y})")
        return

    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        campaign.STATE_DATA.update(state)
        campaign.job=resume_job
        run_day.protected_idle=MiniGuard().preflight
        campaign.status(operation="CHECKING_ACTIVE_RESTART",reason=None,resource_mode="mini_only",
                        physical_time_s=t,last_checkpoint=str(source),restart_readback_required=True)
        total_steps=int(job["steps"])
        _,end,_=campaign.integrate(ACTIVE,source,t,history,total_steps-done,moving=True,options=options)
        gate=state["fixed_gate"]
        fixed_hist=list(analysis.read_samples(campaign.FIXED_STAGE,"history.csv"))
        upstream=[r for r in analysis.read_samples(campaign.FIXED_STAGE,"gauges.csv") if abs(float(r["x_m"])+3)<1e-7]
        start=float(gate["window_s"][0])
        incident=sum(a for _,a in analysis.cycles(upstream,start,period,"eta_actual_m"))/campaign.CYCLES
        analysis.finish_active(origin,end,period,analysis.cycles(fixed_hist,start,period,"CL"),
                               analysis.cycles(fixed_hist,start,period,"CD"),incident,gate)
    except Exception as error:
        campaign.status(operation="HOLD",reason=str(error))
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__=="__main__":
    main("--preflight" in sys.argv)
