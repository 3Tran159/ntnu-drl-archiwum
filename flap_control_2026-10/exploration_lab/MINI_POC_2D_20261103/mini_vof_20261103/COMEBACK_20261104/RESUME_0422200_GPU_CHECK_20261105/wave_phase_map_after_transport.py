"""Continue the verified Mini checkpoint after a transport loss and foreign queue."""
import math
import os
from pathlib import Path
import time

import wave_phase_map_campaign as campaign
from resume import c, D, P, CPUS, run_day
from wave_phase_map_analysis import finish_fixed_and_run_active

FOLDER=P/"runs/PHASE_MAP_WAVE_FIXED_20261106_101415"
SOURCE=FOLDER/"CP_000140_t2.026000.sim"
DIGEST="744e131de23d2b987bc10046541422e1d396bf36fdc2b6cdc19416b379a2f4b6"
WAIT_LOCK=D/"WAVE_PHASE_MAP_RESOURCE_WAIT.lock"

def wait_for_resources():
    until=time.monotonic()+8*3600
    last=""
    while time.monotonic()<until:
        if c.STOP.exists() or c.LOCK.exists():
            raise RuntimeError("Existing STOP marker or Mini owner prevents continuation")
        try:
            run_day.protected_idle()
            return
        except RuntimeError as error:
            reason=str(error)
            if not reason.startswith(("Other STAR/MPI present:", "Independent CFD queue has priority:", "Dedicated port is occupied")):
                raise
            if reason!=last:
                campaign.status(operation="WAITING_FOR_RESOURCES",reason=reason)
                last=reason
        time.sleep(30)
    raise RuntimeError("Foreign queue or STAR session occupied resources for 8 hours")

def main():
    if c.STOP.exists() or c.LOCK.exists():
        raise RuntimeError("STOP marker or live Mini controller")
    state=c.read(campaign.STATE)
    if state["operation"]!="HOLD" or not state["reason"].startswith("Independent CFD queue has priority:"):
        raise RuntimeError("Expected the previous transport/relaunch HOLD")
    if c.sha(SOURCE)!=DIGEST:
        raise RuntimeError("Transport checkpoint SHA-256 mismatch")
    cfg=c.read(FOLDER/"job.json")
    if (cfg["dt"],cfg["inner"],cfg["phase_interface_cfl_max"])!=(campaign.DT,campaign.INNER,campaign.CFL_LIMIT):
        raise RuntimeError("Unexpected numerical settings in the interrupted wave")
    source,t,hist,n=campaign.recover(FOLDER,float(cfg["expected_time"]),int(cfg["steps"]))
    if source!=SOURCE or n!=140 or abs(t-2.026)>1e-9:
        raise RuntimeError("Checkpoint lineage did not verify")
    for segment in state["segments"]:
        if c.sha(Path(segment["checkpoint"]))!=segment["sha256"]:
            raise RuntimeError("Archived trajectory lineage did not verify")
    with WAIT_LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        campaign.STATE_DATA.update(state)
        campaign.STATE_DATA["segments"].append(dict(stage=campaign.FIXED_STAGE,folder=str(FOLDER),
            end_s=t,status="RECOVERED_TRANSPORT",checkpoint=str(source),sha256=DIGEST))
        campaign.status(operation="CHECKING_RESOURCES",reason=None,last_checkpoint=str(source),
                        physical_time_s=t,training_approved=False)
        wait_for_resources()
        with c.LOCK.open("x",encoding="ascii") as lock:
            lock.write(str(os.getpid()))
        try:
            run_day.protected_idle()
            c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in CPUS)
            campaign.status(operation="RESUMING_WAVE_FIXED",reason=None)
            remaining=math.ceil((campaign.START_GATE+campaign.CYCLES*campaign.PERIOD-t)/campaign.DT)
            source,t,hist=campaign.integrate(campaign.FIXED_STAGE,source,t,hist,remaining)
            finish_fixed_and_run_active(source,t,hist)
        finally:
            if not c.filtered_query(c.OWNER):
                c.LOCK.unlink()
    finally:
        WAIT_LOCK.unlink()

if __name__=="__main__":
    try:
        main()
    except (RuntimeError,OSError,ValueError,KeyError) as error:
        if not WAIT_LOCK.exists():
            campaign.status(operation="HOLD",reason=str(error))
        raise
