import os
from pathlib import Path

import night_seed_dataset as night

c, P, D = night.c, night.P, night.D
night.STATE = D/"NIGHT_WAVE_CFL_FALLBACK_STATUS.json"
night.FAST_MACRO = D/"residual_block_macro/MiniVofStokes.java"
folder = P/"runs/N01_WAVE_FIXED_H010_RESUME_20261106_054507"
source = folder/"CP_000280_t1.746000.sim"
expected_sha = "38c230f4129a126fe557919fd5863fca00023ff1cdb13c07638bc59c7309665d"

def launch():
    night.run_day.protected_idle()
    if c.STOP.exists():
        raise RuntimeError("Stop requested")
    old=c.read(folder/"DAY_RESULT.json")
    row=next(row for row in c.tail(folder/"history.csv") if row["step"]=="280")
    if (old["status"]!="HOLD_CFL" or not old["transport_ok"] or c.sha(source)!=expected_sha
            or float(row["interface_CFL"])>.5 or float(row["max_CFL"])>25):
        raise RuntimeError("Pre-CFL checkpoint gate or integrity mismatch")
    history=Path(c.read(folder/"AF_RESUME_HISTORY.json")["path"])
    if not history.is_file():
        raise RuntimeError("Missing archived AF history")
    t=float(row["time_s"])
    origin=float(c.read(folder/"job.json")["ramp_origin_s"])
    steps=int((night.remaining()-270)/4.25)
    if steps<50:
        raise RuntimeError("Insufficient remaining time")
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in night.CPUS)
        night.status(operation="RUNNING_REFERENCE_CFL_FALLBACK", source=str(source),
                     source_sha256=expected_sha, source_t_s=t, wave_origin_s=origin,
                     planned_steps=steps, training_approved=False)
        result=night.do_run("N01_WAVE_FIXED_H010_CFL_FALLBACK",source,t,history,
                            steps=steps,save_interval_s=.01,amplitude=.05,old_amplitude=0,
                            ramp_s=night.RAMP,ramp_origin_s=origin)
        night.status(operation="PARTIAL_WAVE_SAVED" if night.verify_result(result,steps) else "HOLD_WAVE",
                     result=result)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()

if __name__=="__main__":
    try:
        launch()
    except (ValueError,RuntimeError,OSError,KeyError) as error:
        night.status(operation="HOLD",reason=str(error))
        raise
