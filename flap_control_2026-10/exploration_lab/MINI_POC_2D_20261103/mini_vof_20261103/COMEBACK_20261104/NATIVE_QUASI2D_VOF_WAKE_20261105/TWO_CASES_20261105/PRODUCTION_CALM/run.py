from pathlib import Path
import os
import sys

D=Path(__file__).resolve().parent
P=D.parents[2]
sys.path.insert(0,str(P/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"))
import run as c

H=Path(r"H:/NTNU_RESEARCH_ARCHIVE/Active Flaps/Sharp_Sealed_Native_Quasi2D_VOF_STAR2606_20261105")/"02_RUN"
SOURCE=H/"Sharp_Sealed_VOF_RUN.sim"
HISTORY=H/"CALM_VOF_NATIVE_FULL_BAND_FIXED_SMOKE30_20261105_134919_AF_Fixed.simh"
FIXED="CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE"
MOTION="CALM_VOF_NATIVE_FULL_BAND_ACTIVE_PLUS_MINUS_5"
CPUS=[22,23]
DT=.0002

def launch():
    day=c.read(P/"DAY_STATUS.json")
    if day["solver_state"]!="STOPPED" or c.LOCK.exists() or c.STOP.exists() or c.filtered_query(c.OWNER):
        raise RuntimeError("Mini is active or a stop is pending")
    for source in (SOURCE,HISTORY):
        if c.sha(source)!=c.sha(D.parent/"02_RUN"/source.name):
            raise RuntimeError("Published working case checksum mismatch")
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=dict(status="RUNNING",stage=FIXED,source=str(SOURCE),source_history=str(HISTORY),
        initial_physical_time_s=.006,checkpoint_interval_s=.005,motion_authorized=False,cpu_indices=CPUS)
    def status(**kwargs):
        c.status(state,**kwargs)
        c.coex.save(D/"STATUS.json",state)
    try:
        mask=sum(1<<cpu for cpu in CPUS)
        c.local.night_flap.MASK=mask
        c.coex.MASK=mask
        status(operation="STARTING_FROM_02_RUN")
        settings=dict(stokes=True,foil=True,expected_cells=25617,calm_only=True,clean_calm=True,
                      matched_calm=True,pressure_diagnostic_only=True,amplitude=0,old_amplitude=0,
                      dt=DT,inner=20,save_interval_s=.005,af_native=True)
        def job(stage,**options):
            return c.new_job(stage,{**settings,**options},protection=c.NightGuard(None,1.777749),
                macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
        fixed=job(FIXED,source=SOURCE,expected_time=.006,source_af_history=HISTORY.as_posix(),
            matched_calm_fixed=True,moving=False,steps=6000,limit_seconds=21600)
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
            source_af_history=(fixed_run/HISTORY.name).as_posix(),moving=True,flow_cycle=True,
            calm_active_pilot=True,flap_cycle_deg=5,flap_quarter_s=.125,steps=2500,limit_seconds=18000)
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

