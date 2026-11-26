import csv
import json
import os
from pathlib import Path

import night_seed_dataset as night

c, P, D = night.c, night.P, night.D
prior_status = night.STATE
night.STATE = D / "NIGHT_VOF_RECOVERY_STATUS.json"
failed = P / "runs/CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE_20261106_000919"
checkpoint = failed / "CP_000100_t1.226000.sim"
expected_sha = "25afd76be57c5634a9b3428c6b973a3e88b850ebdb5ae67d7939321ca1ce8fd9"

def recover():
    owner = 23488
    if c.STOP.exists() or int(c.LOCK.read_text().strip()) != owner:
        raise RuntimeError("Expected the original overnight controller")
    night.status(operation="WAITING_FOR_INDEPENDENT_MOTION", waits_for_pid=owner,
                 recovery_checkpoint=str(checkpoint), training_approved=False)
    night.wait_for_calm_and_motion(owner)
    night.run_day.protected_idle()
    if c.STOP.exists() or c.LOCK.exists():
        raise RuntimeError("Stop marker or existing controller lock")
    if night.remaining() < 3000:
        raise RuntimeError("Insufficient night budget for bounded CALM recovery")
    cp = c.read(failed / "LATEST_CHECKPOINT.json")
    if (Path(cp["path"]) != checkpoint or not cp["complete_write"]
            or c.sha(checkpoint) != expected_sha or checkpoint.stat().st_size != cp["bytes"]):
        raise RuntimeError("Last complete checkpoint failed verification")
    job = c.read(failed / "job.json")
    with Path(job["fixed_window_seed"]).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    local = c.tail(failed / "history.csv")[:cp["step_in_job"]]
    if len(local) != cp["step_in_job"] or any(abs(float(row["delta_measured_deg"])) > 1e-10 for row in local):
        raise RuntimeError("Recovery history incompatible with fixed flap")
    count = int(job["fixed_elapsed_before"]) + len(local)
    sample = (rows + local)[-(250 + count % 250):]
    for i, row in enumerate(sample):
        if abs(float(row["time_s"]) - (cp["time_s"] - (len(sample)-1-i)*night.DT)) > 1e-9:
            raise RuntimeError("Recovery force history not aligned to checkpoint")
    seed = D / "FIXED_SEED_VOF_RECOVERY_1226000.csv"
    with seed.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, ("time_s","CL","CD"), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sample)
    history = Path(c.read(failed / "AF_RESUME_HISTORY.json")["path"])
    if not history.is_file():
        raise RuntimeError("Missing AF history")
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in night.CPUS)
        night.status(operation="RUNNING_RECOVERED_CALM_FIXED", prior_status=str(prior_status),
                     source_sha256=expected_sha, source_t_s=cp["time_s"])
        result = night.job(night.FIXED, checkpoint, cp["time_s"],
                           source_af_history=history.as_posix(), af_branch_history=False,
                           macro_source=night.FAST_MACRO, matched_calm_fixed=True,
                           fixed_window_seed=seed.as_posix(), fixed_elapsed_before=count,
                           fixed_stable_count=0, moving=False, steps=min(1900, (night.remaining()-900)//6),
                           save_interval_s=.01, limit_seconds=night.remaining()-900)
        c.publish(result)
        night.status(calm_recovery_result=result)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()
    night.run_wave_chain(fixed_result=result)

if __name__ == "__main__":
    try:
        recover()
    except (ValueError, RuntimeError, OSError, KeyError) as error:
        night.status(operation="HOLD", reason=str(error))
        raise
