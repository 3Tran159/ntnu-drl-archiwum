import datetime as dt
import os
import sys
from pathlib import Path
import time

import calm_pair_ready as pair
from night_flap import END, LOCK, OUT, OWNER, STATUS, STOP, archive, coex, query, read

if __name__=="__main__":
    if len(sys.argv)==2:
        prior_pid=int(sys.argv[1])
        while LOCK.exists() and not STOP.exists() and END-time.time()>1200:
            if LOCK.read_text().strip()!=str(prior_pid):
                raise RuntimeError("A different owner holds the controller lock")
            owners=query(f"(Get-Process -Id {prior_pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress")
            if owners!=[prior_pid]:
                raise RuntimeError("Previous owner ended without releasing its lock")
            time.sleep(20)
    if STOP.exists() or query(OWNER) or END-time.time()<1200:
        raise RuntimeError("Manual STOP, active Mini, or insufficient night window")
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    state=read(STATUS)
    try:
        if state["status"]!="REVIEW":
            raise RuntimeError("Expected completed controller session")
        for name in ("CALM_VOF_FIXED_SEALED","CALM_VOF_FIXED_GAP"):
            result=state["runs"].get(name,{})
            if result.get("status")!="HOLD_CFL" or result.get("samples")!=1:
                raise RuntimeError("The paired timestep retry requires a first-step CFL-only hold")
            if (OUT/(name+"_DT020")).exists():
                raise RuntimeError("Already attempted the paired VOF retry")
        archive(STATUS,OUT/("BEFORE_VOF_TIMESTEP_RETRY_"+dt.datetime.now().strftime("%H%M%S")+".json"))
        pair.DSTEP=.0002
        pair.COMMON["dt"]=.0002
        state["vof_timestep_retry"]={"from_s":.00025,"to_s":.0002,"reason":"First-step global CFL above 25; interface CFL below 0.02."}
        pair.run_vof_pair(state,suffix="_DT020")
        state["status"]="STOPPED" if STOP.exists() else "REVIEW"
    except Exception as exc:
        state.update(status="HOLD",reason=str(exc))
        raise
    finally:
        state["active"]=None
        coex.save(STATUS,state)
        if not query(OWNER):
            LOCK.unlink()

