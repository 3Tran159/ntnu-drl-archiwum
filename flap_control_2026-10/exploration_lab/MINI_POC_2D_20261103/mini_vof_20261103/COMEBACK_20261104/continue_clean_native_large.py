"""Continue the coarse CALM pilot only after ten completed physically safe steps."""
import json
import os
from pathlib import Path
import stokes_coexistence as coex
from run_day import HERE,LOCK,STOP,new_job,sha
from run_recovery_calm_komega import protect_w06

meta=json.loads((HERE/"WALL_FUNCTIONS_AUDIT"/"COARSE_FACETED_LARGE_CELLS"/"COARSE_AUDIT.json").read_text())
run=json.loads((HERE/"CLEAN_NATIVE_LARGE_RESULT.json").read_text())["result"]
cp=Path(run["checkpoint"])
dst=HERE/"CLEAN_NATIVE_LARGE_CONT_RESULT.json"
if (STOP.exists() or dst.exists() or run["samples"]!=10 or not run["transport_ok"]
        or run["status"] not in ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW") or sha(cp)!=run["checkpoint_sha256"]):
    raise RuntimeError("Clean CALM smoke has not cleared the hard continuation gates")
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
guard=None
try:
    guard=protect_w06("CLEAN_NATIVE_LARGE_CONT")
    result=new_job("CLEAN_NATIVE_LARGE_CALM_CONT",dict(source=cp,stokes=True,foil=True,calm_only=True,
        clean_calm=True,amplitude=0,old_amplitude=0,expected_time=run["state"]["time_s"],steps=30,
        inner=20,dt=.0145,expected_cells=meta["cells"],buoyancy_reference_N=meta["buoyancy_N"],
        save_interval_s=.145,pressure_urf=.2,pressure_tol=.1,limit_seconds=650),protection=guard)
    coex.save(dst,dict(result=result,W06_peak=guard.peak if guard else None,night_approved=False))
except Exception as exc:
    coex.save(dst,dict(status="HOLD",error=str(exc),W06_stop=guard.stopped if guard else None))
    raise
finally:
    LOCK.unlink()

