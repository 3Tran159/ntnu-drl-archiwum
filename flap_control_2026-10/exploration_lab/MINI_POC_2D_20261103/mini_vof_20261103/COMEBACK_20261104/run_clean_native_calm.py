import json
import os
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

audit=json.loads((HERE/"WALL_FUNCTIONS_AUDIT"/"RECOVERY_V2_TE_PARTIAL"/"RECOVERY_MESH_AUDIT.json").read_text())
mesh=Path(audit["mesh"])
result_path=HERE/"CLEAN_NATIVE_CALM_RESULT.json"
if STOP.exists() or result_path.exists() or sha(mesh)!=audit["mesh_sha256"] or audit["status"]!="OFFLINE_MESH_MOTION_PASS":
    raise RuntimeError("Clean Mini preflight blocked")
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
guard=None
try:
    guard=protect_w06("CLEAN_NATIVE_CALM")
    result=new_job("CLEAN_NATIVE_CALM_FIXED_U18",dict(stokes=True,fresh=True,foil=True,calm_only=True,
        clean_calm=True,amplitude=0,old_amplitude=0,expected_time=0,steps=10,inner=20,dt=.00005,
        pressure_urf=.2,pressure_tol=.1,mesh_override=mesh.as_posix(),mesh_override_sha256=audit["mesh_sha256"],
        limit_seconds=650),protection=guard)
    coex.save(result_path,dict(result=result,W06_peak=guard.peak if guard else None,
        W06_stop=guard.stopped if guard else None,night_approved=False))
except Exception as err:
    coex.save(result_path,dict(status="HOLD",error=str(err),W06_stop=guard.stopped if guard else None))
    raise
finally:
    LOCK.unlink()

