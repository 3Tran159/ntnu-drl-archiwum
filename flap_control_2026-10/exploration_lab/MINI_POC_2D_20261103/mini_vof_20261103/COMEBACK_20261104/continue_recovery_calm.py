"""Continue the accepted low-speed CALM ramp without reinitializing its fields."""
import csv
import json
import os
from pathlib import Path

from run_day import HERE, LOCK, STOP, new_job, sha
import stokes_coexistence as coex
from run_recovery_calm_komega import protect_w06

PREVIOUS = HERE/"RECOVERY_CALM_RAMP_KOMEGA_RESULT.json"
RESULT = HERE/"RECOVERY_CALM_CONTINUE_RESULT.json"

def main():
    if STOP.exists() or RESULT.exists():
        raise RuntimeError("STOP or existing continuation requires review")
    data=json.loads(PREVIOUS.read_text())
    report=data["result"]
    source=Path(report["checkpoint"])
    if (report["samples"]!=40 or not report["transport_ok"]
            or report["status"] not in ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW")
            or sha(source)!=report["checkpoint_sha256"] or data.get("W06",{}).get("stop")):
        raise RuntimeError("Low-speed ramp smoke did not complete the hard gates")
    with LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    watcher=None
    try:
        watcher=protect_w06("RECOVERY_CONT")
        result=new_job("RECOVERY_CALM_RAMP_CONTINUE",dict(
            source=source,expected_time=report["state"]["time_s"],stokes=True,calm_only=True,
            foil=True,amplitude=0,old_amplitude=0,dt=.0001,inner=20,steps=100,
            calm_speed_ramp_s=.05,calm_explicit_ambient=True,save_interval_s=.005,
            limit_seconds=840),protection=watcher)
        folder=Path(result["checkpoint"]).parent
        with (folder/"history.csv").open(encoding="utf8") as f:
            rows=list(csv.DictReader(f))
        status={"result":result,"target_speed_reached":bool(rows) and float(rows[-1]["Ux_theory"])>=17.99,
            "final_inlet_target_m_s":float(rows[-1]["Ux_theory"]) if rows else None,
            "night_approved":False}
        if watcher:
            status["W06"]=dict(baseline_s=watcher.baseline,peak_slowdown=watcher.peak,stop=watcher.stopped)
        coex.save(RESULT,status)
    except Exception as exc:
        coex.save(RESULT,dict(status="HOLD",error=str(exc),W06_stop=watcher.stopped if watcher else None))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

