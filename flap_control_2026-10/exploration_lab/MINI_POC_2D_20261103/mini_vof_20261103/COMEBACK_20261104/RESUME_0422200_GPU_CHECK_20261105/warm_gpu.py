import csv
import json
import os
from pathlib import Path
import time

import resume as r
from resume import c, D, P, FIXED, MOTION, CPUS, DT, job, run_day

PREVIOUS = P / "runs/CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE_20261105_173753"
BENCH_CPU = P / "runs/CALM_VOF_BENCH_CPU_20261105_172034"
STATE = D / "WARM_GPU_STATUS.json"
STOP_TEXT = "Pause production at a completed step for bounded GPU warmup benchmark"
TIMEOUT_TEXT = "Native heartbeat stale; request graceful stop."
state = {}


def update(**items):
    state.update(items)
    c.coex.save(STATE, state)


def main():
    day = c.read(P / "DAY_STATUS.json")
    if (Path(day["output"]) != PREVIOUS or day["solver_state"] != "RUNNING"
            or not c.LOCK.exists() or c.STOP.exists()):
        raise RuntimeError("Expected the running CALM/FIXED production case")
    cpu_result = c.read(BENCH_CPU / "DAY_RESULT.json")
    original = c.read(r.SOURCE_RUN / "DAY_RESULT.json")
    start = original["state"]["time_s"]
    source = Path(original["checkpoint"])
    if c.sha(source) != cpu_result["checkpoint_sha256_input"]:
        raise RuntimeError("Benchmark source checksum mismatch")
    cpu = r.benchmark_receipt("CPU", cpu_result, start)
    benchmark_history = Path(c.read(r.SOURCE_RUN / "AF_RESUME_HISTORY.json")["path"])
    if not benchmark_history.is_file() or not (D / "MiniVofStokes.java").is_file():
        raise RuntimeError("Benchmark prerequisites missing")
    with c.STOP.open("x", encoding="ascii") as stream:
        stream.write(STOP_TEXT)
    update(operation="CHECKPOINTING_PRODUCTION")
    deadline = time.monotonic() + 180
    while c.LOCK.exists() and time.monotonic() < deadline:
        time.sleep(3)
    run_day.protected_idle()
    if c.LOCK.exists() or c.STOP.read_text() != STOP_TEXT:
        raise RuntimeError("Production stop not verified")
    day = c.read(P / "DAY_STATUS.json")
    prior = c.read(PREVIOUS / "DAY_RESULT.json")
    prod = Path(prior["checkpoint"])
    start_prod = prior["state"]["time_s"]
    if (day["solver_state"] != "STOPPED" or Path(day["output"]) != PREVIOUS
            or prior["status"] != "HOLD_STOP_OR_DEADLINE" or not prior["transport_ok"]
            or c.sha(prod) != prior["checkpoint_sha256"]):
        raise RuntimeError("Production checkpoint verification failed")
    prod_history = Path(c.read(PREVIOUS / "AF_RESUME_HISTORY.json")["path"])
    history = c.tail(r.SOURCE_RUN / "history.csv") + c.tail(PREVIOUS / "history.csv")
    total = 501 + len(history)
    old_gate = c.read((PREVIOUS if (PREVIOUS / "CALM_FIXED_PROGRESS.json").exists() else
                       r.SOURCE_RUN) / "CALM_FIXED_PROGRESS.json")
    seed = D / "FIXED_SEED_AFTER_WARM_GPU.csv"
    rows = history[-(250 + total % 250):]
    for i, row in enumerate(rows):
        if (abs(float(row["time_s"]) - (start_prod - (len(rows) - 1 - i) * DT)) > 1e-9
                or abs(float(row["delta_measured_deg"])) > 1e-10):
            raise RuntimeError("Production force history does not align with restart")
    with seed.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, ("time_s", "CL", "CD"), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with c.LOCK.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        c.STOP.rename(D / "STOP_FOR_WARM_GPU_ARCHIVED")
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in CPUS)
        update(operation="GPU_WARMUP_BENCHMARK", production_checkpoint=str(prod),
               production_time_s=start_prod, cpu_solver_s=cpu["result"]["solver_step_median_s"],
               cpu_wall_s=cpu["wall_step_median_s"])
        use_gpu = False
        try:
            result = job("CALM_VOF_BENCH_GPU_WARM", source, start, gpu=True,
                         source_af_history=benchmark_history.as_posix(), af_branch_history=False,
                         moving=False, steps=r.N, limit_seconds=1000)
            gpu = r.benchmark_receipt("GPU", result, start)
            errors = {key: max(abs(float(x[key]) - float(y[key])) / max(abs(float(x[key])), 1e-12)
                               for x, y in zip(cpu["rows"], gpu["rows"]))
                      for key in ("CL", "CD", "Mh")}
            use_gpu = (max(errors.values()) <= .005 and
                       gpu["wall_step_median_s"] < .95 * cpu["wall_step_median_s"])
            update(gpu_result=result, gpu_wall_s=gpu["wall_step_median_s"], max_relative_differences=errors)
        except (RuntimeError, OSError, KeyError, ValueError) as error:
            run_day.protected_idle()
            if c.STOP.exists():
                if c.STOP.read_text() != TIMEOUT_TEXT:
                    raise
                c.STOP.rename(D / "STOP_WARM_GPU_TIMEOUT")
            failure = c.read(P / "DAY_STATUS.json")
            receipt = Path(failure["output"]) / "ERROR.json"
            update(gpu_hold=c.read(receipt)["error"] if receipt.is_file() else str(error))
        update(operation="PRODUCTION_FIXED", selected="GPU" if use_gpu else "CPU")
        fixed = job(FIXED, prod, start_prod, gpu=use_gpu, source_af_history=prod_history.as_posix(),
                    af_branch_history=False, moving=False, matched_calm_fixed=True,
                    fixed_window_seed=seed.as_posix(), fixed_stable_count=old_gate["stable_windows"],
                    fixed_elapsed_before=total, steps=6000-total, limit_seconds=21600)
        c.publish(fixed)
        gate = fixed.get("stabilization", {})
        update(fixed_result=fixed)
        if (c.STOP.exists() or fixed["status"] != "PASS_CALM_FORCE_STABILIZATION"
                or not fixed["transport_ok"] or gate.get("stable_windows") != 3
                or not (gate["CL_drift_fraction"] < .005 and gate["CD_drift_fraction"] < .005)
                or abs(gate["time_s"] - fixed["state"]["time_s"]) > 1e-9):
            update(operation="HOLD_FIXED_GATE")
            return
        cp = Path(fixed["checkpoint"])
        if c.sha(cp) != fixed["checkpoint_sha256"]:
            raise RuntimeError("Stabilized checkpoint checksum mismatch")
        last = c.tail(cp.parent / "history.csv")[-1]
        if any(abs(float(last[k])) > 1e-10 for k in ("delta_measured_deg", "delta_command_deg")):
            raise RuntimeError("Stabilized flap angle is not zero")
        update(operation="PRODUCTION_MOTION", motion_backend="CPU")
        active = job(MOTION, cp, gate["time_s"], source_af_history=Path(
                     c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"]).as_posix(),
                     moving=True, flow_cycle=True, calm_active_pilot=True, flap_cycle_deg=5,
                     flap_quarter_s=.125, steps=2500, limit_seconds=18000)
        c.publish(active)
        update(operation="MOTION_FINISHED", motion_result=active)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        update(operation="HOLD", reason=str(error))
        raise
