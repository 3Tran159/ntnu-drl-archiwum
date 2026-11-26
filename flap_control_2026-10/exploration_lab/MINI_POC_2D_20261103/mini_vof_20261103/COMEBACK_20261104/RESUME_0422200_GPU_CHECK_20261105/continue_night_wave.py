import math
import os
from pathlib import Path
import time

import night_seed_dataset as night
import timestep_screen as screen

c, P, D = night.c, night.P, night.D
night.STATE = D / "NIGHT_WAVE_CONTINUATION_STATUS.json"
night.FAST_MACRO = D / "residual_block_macro/MiniVofStokes.java"
failed = P / "runs/N01_WAVE_FIXED_H010_STARTUP_20261106_050234"
checkpoint = failed / "CP_000500_t1.606000.sim"
expected_sha = "d908d81c007475e3c5acbe39105d0570980ec02ed0a82ae58cbf2bc37c745c8b"

def continue_wave():
    night.status(operation="WAITING_FOR_OWNED_WAVE_CLOSE", training_approved=False)
    until = time.monotonic()+90
    while time.monotonic()<until:
        active = c.filtered_query(night.run_day.READ)
        if not any(p["ProcessId"] in {10796,32216,6568} for p in active) and not c.filtered_query(c.OWNER):
            break
        time.sleep(3)
    else:
        raise RuntimeError("Owned wave session remains present")
    night.run_day.protected_idle()
    if c.STOP.exists() or not c.LOCK.exists() or c.LOCK.read_text().strip()!="16164":
        raise RuntimeError("Original wave controller lock or stop marker changed")
    c.LOCK.rename(D/"STALE_DIRECT_WAVE_CONTROLLER_16164.lock")
    cp = c.read(failed/"LATEST_CHECKPOINT.json")
    if (Path(cp["path"]) != checkpoint or not cp["complete_write"]
            or checkpoint.stat().st_size != cp["bytes"] or c.sha(checkpoint) != expected_sha):
        raise RuntimeError("WAVE source checkpoint failed integrity check")
    settings = c.read(failed/"job.json")
    origin = float(settings["ramp_origin_s"])
    history = Path(c.read(failed/"AF_RESUME_HISTORY.json")["path"])
    if not history.is_file():
        raise RuntimeError("Missing WAVE AF history")
    t = cp["time_s"]
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in night.CPUS)
        opts = dict(amplitude=.05, old_amplitude=0, ramp_s=night.RAMP, ramp_origin_s=origin)
        selected = screen.CONFIGS[0]
        observed_step = 4.5
        night.status(operation="WAVE_MATCHED_STEP_COMPARISON", wave_origin_s=origin,
                     source=str(checkpoint), source_t_s=t, source_sha256=expected_sha)
        if night.remaining() >= 2650:
            ref = None
            for config in (selected, screen.CONFIGS[-1]):
                label, dt, inner = config
                try:
                    steps = round(screen.DURATION/dt)
                    result = night.do_run("WAVE_QUAL_"+label, checkpoint, t, history,
                                          steps=steps, dt=dt, inner=inner, **opts)
                    fields, meta = screen.receipt(result,t,steps,dt)
                    if ref is None:
                        ref = (fields,meta)
                        observed_step = meta["full_s_per_step"]
                        night.status(reference=meta)
                    else:
                        matches,differences=screen.compare(ref[0],fields)
                        passed=matches and meta["wall_s_per_physical_s"] < .95*ref[1]["wall_s_per_physical_s"]
                        if passed:
                            selected=config
                            observed_step=meta["full_s_per_step"]
                        night.status(candidate=meta, comparison=differences, short_wave_screen_pass=passed)
                except (ValueError,RuntimeError,OSError,KeyError) as error:
                    night.status(qualification_hold=str(error))
                    night.run_day.protected_idle()
                    break
        if night.remaining()<600 or c.STOP.exists():
            raise RuntimeError("Insufficient night budget or stop requested")
        label, dt, inner = selected
        steps = min(math.ceil((origin+.72-t)/dt), int((night.remaining()-260)/max(3.1,observed_step*1.18)))
        if steps<25:
            raise RuntimeError("No safe budget for WAVE continuation")
        night.status(operation="RUNNING_WAVE_FIXED_CONTINUATION", selected=selected, planned_steps=steps)
        result=night.do_run("N01_WAVE_FIXED_H010_RESUME",checkpoint,t,history,steps=steps,
                            dt=dt,inner=inner,save_interval_s=.01,**opts)
        night.status(operation="PARTIAL_WAVE_SAVED" if night.verify_result(result,steps) else "HOLD_WAVE",
                     result=result)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()

if __name__=="__main__":
    try:
        continue_wave()
    except (ValueError,RuntimeError,OSError,KeyError) as error:
        night.status(operation="HOLD",reason=str(error))
        raise
