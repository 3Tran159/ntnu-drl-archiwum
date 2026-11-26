"""Run ten bounded warm-start steps on the protected Mini controller."""
import json
import os
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

C01_READ = HERE/"RECOVERY_V3_C01_READBACK.json"
RESULT = HERE/"RECOVERY_V3_CALM_NATIVE_RESULT.json"
MESH = HERE/"WALL_FUNCTIONS_AUDIT"/"RECOVERY_V2_TE_PARTIAL"/"RECOVERY_MESH_AUDIT.json"

def main():
    if STOP.exists() or RESULT.exists():
        raise RuntimeError("Mini stop or previous V3 result requires review")
    source=json.loads(C01_READ.read_text())
    folder=Path(source["run_directory"])
    readback=json.loads((folder/"REOPEN.json").read_text())
    if readback["steps"]!=0 or abs(readback["time_s"]-4.6992)>1e-8:
        raise RuntimeError("Unexpected C01 readback")
    mesh=json.loads(MESH.read_text())
    seed=folder/"MINI_C01_INITIAL.csv"
    seed_data=json.loads(seed.with_suffix(".json").read_text())
    if sha(seed)!=seed_data["seed_sha256"] or sha(Path(mesh["mesh"]))!=mesh["mesh_sha256"]:
        raise RuntimeError("Input V3 hash check failed")
    with LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    guard=None
    try:
        guard=protect_w06("RECOVERY_V3_NATIVE_MINI")
        run=new_job("RECOVERY_V3_C01_WARM_CALM_NATIVE",dict(
            source=Path(r"F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\mini_vof_20261103\COMEBACK_20261104\runs\RECOVERY_V3_C01_WARM_CALM_20261104_110145\START.sim"),stokes=True,foil=True,calm_only=True,c01_seeded=True,
            amplitude=0,old_amplitude=0,expected_time=0,steps=10,inner=20,dt=.00005,
            limit_seconds=650),protection=guard)
        coex.save(RESULT,dict(result=run,W06_peak=guard.peak if guard else None,
            next="REVIEW_CALM_ONLY",night_approved=False))
    except Exception as err:
        coex.save(RESULT,dict(status="HOLD",error=str(err),W06_stop=guard.stopped if guard else None))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()



