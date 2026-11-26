from pathlib import Path
import json
import os
import sys
import time

D=Path(__file__).resolve().parent
OUT=D.parent
ROOT=OUT.parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

def main():
    output=D/"RESULT.json"
    prev=json.loads((OUT/"DT025_RESULT.json").read_text())
    status=json.loads((HERE/"DAY_STATUS.json").read_text())
    if output.exists() or STOP.exists() or prev["status"]!="HOLD" or status["solver_state"]!="STOPPED":
        raise RuntimeError("Sharp sealed resume preflight blocked")
    prefix=Path(status["output"])
    receipt=json.loads((prefix/"LATEST_CHECKPOINT.json").read_text())
    source=Path(receipt["path"])
    archive=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104\SHARP_SEALED_FIXED_0P600S.sim")
    if (not receipt["complete_write"] or abs(receipt["time_s"]-.6)>1e-9
        or source.parent!=prefix or source.stat().st_size!=receipt["bytes"]
        or sha(source)!=sha(archive)):
        raise RuntimeError("Saved sharp sealed checkpoint mismatch")
    mesh=json.loads((ROOT/"SEALED_SHARP_MATCHED_OUTER"/"MESH_AUDIT.json").read_text())
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        guard=protect_w06("MATCHED_FIXED_SHARP_SEALED_RESUME0600_"+time.strftime("%H%M%S"))
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),initial_time_s=.6))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_RESUME0600",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],
            expected_time=.6,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,
            dt=.00025,steps=800,fixed_protocol=True,seeded_single_phase=True,
            fixed_from_unsteady=True,restore_fixed_history=True,
            fixed_prefix_directory=prefix.as_posix(),after_fixed_motion=True,limit_seconds=5600),
            protection=guard,macro_source=D/"MiniVofStokes.java")
        case=Path(result["checkpoint"]).parent
        result["fixed"]=json.loads((case/"FIXED_PROTOCOL.json").read_text())
        result["W06"]=dict(peak=guard.peak,stop=guard.stopped) if guard else None
        coex.save(output,result)
    except Exception as e:
        coex.save(output,dict(status="HOLD",error=str(e)))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

