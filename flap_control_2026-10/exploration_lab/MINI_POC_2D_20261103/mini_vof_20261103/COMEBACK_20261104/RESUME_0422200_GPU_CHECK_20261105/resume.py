import csv
import math
import os
from pathlib import Path
from statistics import median
import sys

D = Path(__file__).resolve().parent
P = D.parent
sys.path.insert(0, str(P / "FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"))
import run as c
import run_day

SOURCE_RUN = P / "runs/CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE_20261105_151256"
FIXED = "CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE"
MOTION = "CALM_VOF_NATIVE_FULL_BAND_ACTIVE_PLUS_MINUS_5"
DT = 0.0002
CPUS = [22, 23]
N = 25
state = {}


def status(**values):
    state.update(values)
    c.coex.save(D / "STATUS.json", state)


def job(stage, source, start, gpu=False, macro_source=None, **options):
    run_day.protected_idle()
    settings = dict(stokes=True, foil=True, expected_cells=25617, calm_only=True,
                    clean_calm=True, matched_calm=True, pressure_diagnostic_only=True,
                    amplitude=0, old_amplitude=0, dt=DT, inner=20, af_native=True,
                    source=source, expected_time=start, save_interval_s=.02,
                    gpu_requested=gpu)
    return run_day.new_job(stage, {**settings, **options},
                           protection=None if gpu else c.NightGuard(None, 1.777749),
                           macro_source=macro_source or (D if gpu else SOURCE_RUN) / "MiniVofStokes.java",
                           mpi_cpu_indices=None if gpu else CPUS, gpu=gpu)


def benchmark(gpu, source, start, history):
    label = "GPU" if gpu else "CPU"
    status(operation="BENCHMARK_" + label)
    result = job("CALM_VOF_BENCH_" + label, source, start, gpu=gpu,
                 source_af_history=history.as_posix(), af_branch_history=False,
                 moving=False, steps=N, limit_seconds=780)
    return benchmark_receipt(label, result, start)


def benchmark_receipt(label, result, start):
    out = Path(result['checkpoint']).parent
    if (not result["transport_ok"] or result["status"] != "NUMERICAL_END_PASS"
            or result["samples"] != N or abs(result["state"]["time_s"] - start - N * DT) > 1e-9):
        raise RuntimeError(f"{label} benchmark failed: {result['status']} {result['state']['reason']}")
    steps = c.tail(out / "history.csv")
    with (out / "step_wall.csv").open(newline="") as f:
        timings = list(csv.reader(f))
    wall = [float(row[1]) for row in timings[6:]]
    if len(wall) != N - 5:
        raise RuntimeError("Benchmark timing window mismatch")
    return dict(result=result, wall_step_median_s=median(wall), rows=steps)


def launch():
    run_day.protected_idle()
    original = c.read(SOURCE_RUN / "DAY_RESULT.json")
    day = c.read(P / "DAY_STATUS.json")
    start = original["state"]["time_s"]
    source = Path(original["checkpoint"])
    previous = c.tail(SOURCE_RUN / "history.csv")
    history = Path(c.read(SOURCE_RUN / "AF_RESUME_HISTORY.json")["path"])
    gate = c.read(SOURCE_RUN / "CALM_FIXED_PROGRESS.json")
    total = 501 + len(previous)
    retry_gpu = "--retry-gpu" in sys.argv
    force_cpu = "--cpu-after-gpu-timeout" in sys.argv
    reuse_cpu = force_cpu or retry_gpu or "--continue-after-cpu" in sys.argv
    if retry_gpu:
        run = Path(day["output"])
        if (day["stage"] != FIXED or day["operation"] != "HOLD" or (run / "native_status.json").exists()
                or c.STOP.exists() or (D / "STOP_BEFORE_GPU_RETRY").read_text() != "Pause owned CPU startup for corrected GPU benchmark"):
            raise RuntimeError("CPU startup interruption has not been verified")
        cpu_result = c.read(P / "runs/CALM_VOF_BENCH_CPU_20261105_172034/DAY_RESULT.json")
    elif force_cpu:
        run = Path(day["output"])
        if (day["stage"] != "CALM_VOF_BENCH_GPU" or day["solver_state"] != "STOPPED"
                or run.name != "CALM_VOF_BENCH_GPU_20261105_173103"
                or c.STOP.read_text() != "Native heartbeat stale; request graceful stop."):
            raise RuntimeError("GPU timeout stop not verified")
        cpu_result = c.read(P / "runs/CALM_VOF_BENCH_CPU_20261105_172034/DAY_RESULT.json")
    elif reuse_cpu:
        if day.get("stage") != "CALM_VOF_BENCH_CPU":
            raise RuntimeError("Unexpected CPU benchmark source")
        cpu_result = c.read(Path(day["output"]) / "DAY_RESULT.json")
    if reuse_cpu:
        if cpu_result["checkpoint_sha256_input"] != original["checkpoint_sha256"]:
            raise RuntimeError("CPU benchmark source hash mismatch")
        cpu = benchmark_receipt("CPU", cpu_result, start)
    if (day["solver_state"] != "STOPPED" or (not reuse_cpu and Path(day["output"]) != SOURCE_RUN)
            or (not (retry_gpu or force_cpu) and (c.STOP.exists() if reuse_cpu else (not c.STOP.exists() or c.STOP.stat().st_size != 0)))
            or abs(start - .4222) > 1e-9 or c.sha(source) != original["checkpoint_sha256"]
            or c.sha(history) != "6206eed8c04c82d4373ed6046d96ced3d7b3c50dbc28a5be219adbb5de441501"
            or len(previous) != original["state"]["steps"]):
        raise RuntimeError("Paused checkpoint, history or stop marker mismatch")
    seed = D / "FIXED_SEED.csv"
    rows = previous[-(250 + total % 250):]
    for index, row in enumerate(rows):
        if (abs(float(row["time_s"]) - (start - (len(rows) - 1 - index) * DT)) > 1e-9
                or any(abs(float(row[k])) > 1e-10 for k in ("delta_measured_deg", "delta_command_deg"))):
            raise RuntimeError("Fixed force history does not align with checkpoint")
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << cpu for cpu in CPUS)
        if force_cpu:
            c.STOP.rename(D / "STOP_GPU_HEARTBEAT_TIMEOUT")
        if not reuse_cpu:
            c.STOP.rename(D / "STOP_AFTER_USER_SHUTDOWN")
            with seed.open("x", newline="") as f:
                writer = csv.DictWriter(f, ("time_s", "CL", "CD"), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        status(status="RUNNING", source=str(source), start_s=start, cpu_indices=CPUS, motion_authorized=False)
        if not reuse_cpu:
            cpu = benchmark(False, source, start, history)
        status(cpu={k:v for k,v in cpu.items() if k != "rows"})
        use_gpu = False
        if force_cpu:
            status(gpu_hold="GPU heartbeat timed out; test stopped at the next safe boundary.")
        else:
            try:
                gpu = benchmark(True, source, start, history)
                errors = {}
                for key in ("CL", "CD", "Mh"):
                    pairs = [(float(a[key]), float(b[key])) for a,b in zip(cpu["rows"], gpu["rows"])]
                    errors[key] = max(abs(a-b)/max(abs(a),1e-12) for a,b in pairs)
                use_gpu = (max(errors.values()) <= .005 and
                           gpu["wall_step_median_s"] < .95 * cpu["wall_step_median_s"])
                status(gpu={k:v for k,v in gpu.items() if k != "rows"}, max_relative_differences=errors)
            except (RuntimeError, OSError, KeyError, ValueError) as error:
                if c.STOP.exists() or run_day.query(run_day.READ):
                    raise
                failed = c.read(P / "DAY_STATUS.json")
                receipt = Path(failed["output"]) / "ERROR.json"
                detail = c.read(receipt)["error"] if receipt.is_file() else str(error)
                status(gpu_hold=detail)
        status(operation="PRODUCTION_FIXED", selected="GPU" if use_gpu else "CPU")
        fixed = job(FIXED, source, start, gpu=use_gpu, source_af_history=history.as_posix(),
                    af_branch_history=False, moving=False, matched_calm_fixed=True,
                    fixed_window_seed=seed.as_posix(), fixed_stable_count=gate["stable_windows"],
                    fixed_elapsed_before=total, steps=6000-total, limit_seconds=21600)
        c.publish(fixed)
        gate = fixed.get("stabilization", {})
        status(fixed_result=fixed)
        if (c.STOP.exists() or fixed["status"] != "PASS_CALM_FORCE_STABILIZATION"
                or not fixed["transport_ok"] or gate.get("stable_windows") != 3
                or not (gate["CL_drift_fraction"] < .005 and gate["CD_drift_fraction"] < .005)
                or abs(gate["time_s"] - fixed["state"]["time_s"]) > 1e-9):
            status(status="HOLD", operation="FIXED_GATE_NOT_PASSED")
            return
        cp = Path(fixed["checkpoint"])
        if c.sha(cp) != fixed["checkpoint_sha256"]:
            raise RuntimeError("Stabilized checkpoint SHA mismatch")
        last = c.tail(cp.parent / "history.csv")[-1]
        if any(abs(float(last[k])) > 1e-10 for k in ("delta_measured_deg", "delta_command_deg")):
            raise RuntimeError("Stabilized state is not fixed at zero degrees")
        status(operation="PRODUCTION_MOTION", motion_authorized=True, motion_backend="CPU")
        active = job(MOTION, cp, gate["time_s"], source_af_history=Path(
                     c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"]).as_posix(),
                     moving=True, flow_cycle=True, calm_active_pilot=True, flap_cycle_deg=5,
                     flap_quarter_s=.125, steps=2500, limit_seconds=18000)
        c.publish(active)
        status(status="REVIEW", operation="MOTION_FINISHED", motion_result=active)
    except Exception as error:
        status(status="HOLD", operation="STOPPED_OR_REVIEW", reason=str(error))
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    launch()
