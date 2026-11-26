from datetime import datetime
import math
import os
import sys
from pathlib import Path
import time

import numpy as np
from resume import c, D, P, CPUS, DT, FIXED, MOTION, job, run_day
import csv
import ctypes
from ctypes import wintypes
import timestep_screen as screen

START = datetime.fromisoformat("2026-11-05T21:00:00+01:00").timestamp()
END = datetime.fromisoformat("2026-11-06T07:00:00+01:00").timestamp()
STATE = D / "NIGHT_SEED_DATASET_STATUS.json"
FAST_MACRO = D / "residual_cache_macro/MiniVofStokes.java"
RAMP = .456
SETTLE = 1.05
FIXED_DURATION = 2.0
WAVE_STARTUP_STEPS = 3600
ACTIVE_STEPS = 2000
FIXED_CASE = "N01_WAVE_FIXED_H010"
ACTIVE_CASE = "N02_WAVE_ACTIVE_H010_TWO_PULSES"
ST = {}
DIRECT_BATCH = False


def status(**items):
    ST.update(items)
    c.coex.save(STATE, ST)


def remaining():
    return int(END - time.time() - 300)


def do_run(label, checkpoint, t, history, *, steps, moving=False, **options):
    limit = remaining()
    if limit < 600 or c.STOP.exists():
        raise RuntimeError("Night budget or stop marker prevents launch")
    result = job(label, checkpoint, t, source_af_history=history.as_posix(), af_branch_history=False,
                 calm_only=False, clean_calm=False, from_calm=not moving, moving=moving, macro_source=FAST_MACRO,
                 steps=steps, limit_seconds=limit, direct_batch=DIRECT_BATCH, **options)
    c.publish(result)
    return result


def signal_fit(times, values, omega):
    phase = omega * times
    a, b, mean = np.linalg.lstsq(
        np.column_stack((np.sin(phase), np.cos(phase), np.ones(len(phase)))), values, rcond=None
    )[0]
    return float(mean), float(math.hypot(a, b)), float(math.atan2(b, a))


def fixed_gate(folder, origin, dt):
    period = float(c.read(folder / "STOKES_AFTER_FIRST_STEP.json")["native_period_s"])
    if not .40 < period < .52:
        return {"pass": False, "reason": "Unexpected native encounter period", "period_s": period}
    omega = 2 * math.pi / period
    start, stop = origin + SETTLE, origin + SETTLE + 2 * period
    hist = c.tail(folder / "history.csv")
    if not hist or float(hist[-1]["time_s"]) < stop - dt:
        return {"pass": False, "reason": "Two post-ramp cycles unavailable", "period_s": period}
    gauge = c.tail(folder / "gauges.csv")
    checks = {}
    for x in (-3, .952):
        rows = [v for v in gauge if abs(float(v["x_m"]) - x) < 1e-6 and start <= float(v["time_s"]) < stop]
        if len(rows) < int(1.9 * period / dt):
            return {"pass": False, "reason": f"Missing gauge coverage at x={x}"}
        ts = np.array([float(v["time_s"]) for v in rows])
        measured, reference = ([float(v[k]) for v in rows] for k in ("eta_actual_m", "eta_native_theory_m"))
        _, amp, phase = signal_fit(ts, measured, omega)
        _, ref_amp, ref_phase = signal_fit(ts, reference, omega)
        checks[str(x)] = dict(amplitude_m=amp, theoretical_amplitude_m=ref_amp,
                              amplitude_error=abs(amp / ref_amp - 1) if ref_amp > 1e-6 else 1e6,
                              phase_error_deg=abs(math.degrees(math.remainder(phase-ref_phase, 2*math.pi))))
    drifts = {}
    for key in ("CL", "CD"):
        means = [np.mean([float(v[key]) for v in hist if start+i*period <= float(v["time_s"]) < start+(i+1)*period])
                 for i in (0, 1)]
        drifts[key] = float(abs(means[1] - means[0]) / max(abs(means[0]), 1e-10))
    passed = (checks["-3"]["amplitude_error"] <= .15 and checks["0.952"]["amplitude_error"] <= .25
              and max(v["phase_error_deg"] for v in checks.values()) <= 20
              and max(drifts.values()) <= .01)
    return {"pass": bool(passed), "period_s": period, "gauges": checks, "cycle_mean_relative_drift": drifts}


def verify_result(result, steps):
    return (result.get("transport_ok") and result.get("status") == "NUMERICAL_END_PASS"
            and result.get("samples") == steps)


def wait_for_calm_and_motion(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    owner = kernel.OpenProcess(0x00100000, False, pid)
    if not owner:
        raise RuntimeError("Cannot verify current Mini controller")
    refresh = 0
    try:
        while time.time() < END - 300:
            if c.STOP.exists():
                raise RuntimeError("Stop marker observed; no additional launch")
            if time.monotonic() >= refresh:
                live = c.read(P / "DAY_STATUS.json")
                folder = Path(live["output"])
                drift = folder / "CALM_FIXED_PROGRESS.json"
                checkpoint = folder / "LATEST_CHECKPOINT.json"
                status(observed_at=datetime.now().astimezone().isoformat(),
                       live_stage=live.get("stage"), live_operation=live.get("operation"),
                       physical_time_s=live.get("physical_time"),
                       last_gate=c.read(drift) if drift.is_file() else None,
                       last_checkpoint=c.read(checkpoint) if checkpoint.is_file() else None)
                refresh = time.monotonic() + 900
            result = kernel.WaitForSingleObject(owner, 5000)
            if result == 0:
                return
            if result != 258:
                raise RuntimeError("Mini controller wait failed")
    finally:
        kernel.CloseHandle(owner)
    raise RuntimeError("Night window elapsed while waiting for existing work")


def extend_calm(fixed):
    gate = fixed.get("stabilization", {})
    if (fixed.get("status") != "HOLD_CALM_FORCE_DRIFT" or not fixed.get("transport_ok")
            or not fixed.get("state", {}).get("residual_pass") or c.STOP.exists()):
        return fixed
    cp = Path(fixed["checkpoint"])
    folder = cp.parent
    if c.sha(cp) != fixed["checkpoint_sha256"]:
        raise RuntimeError("CALM extension source checksum mismatch")
    old = c.read(folder / "job.json")
    rows = c.tail(folder / "history.csv")
    t = fixed["state"]["time_s"]
    count = int(old["fixed_elapsed_before"]) + len(rows)
    offset = count % 250
    sample = rows[-(750+offset):len(rows)-offset if offset else len(rows)]
    if len(sample) != 750:
        return fixed
    means = [float(np.mean([float(row["CD"]) for row in sample[i:i+250]]))
             for i in (0,250,500)]
    preceding = abs(means[1]-means[0])/max(abs(means[0]),1e-10)
    latest = float(gate.get("CD_drift_fraction",1))
    if not (.0 < latest <= .015 and latest <= preceding*1.02
            and float(gate.get("CL_drift_fraction",1)) < .01):
        status(calm_extension_reason="Last windows do not justify an extension",
               calm_latest_drag_drift=latest, calm_previous_drag_drift=preceding)
        return fixed
    steps = min(2000, int((remaining()-240-2700)/5))
    if steps < 500:
        return fixed
    seed_rows = rows[-(250+offset):]
    for i,row in enumerate(seed_rows):
        if abs(float(row["time_s"])-(t-(len(seed_rows)-1-i)*DT))>1e-9 or abs(float(row["delta_measured_deg"]))>1e-10:
            raise RuntimeError("CALM extension seed history inconsistent")
    seed = D / "FIXED_SEED_NIGHT_EXTENSION.csv"
    with seed.open("x",newline="") as stream:
        writer=csv.DictWriter(stream,("time_s","CL","CD"),extrasaction="ignore")
        writer.writeheader()
        writer.writerows(seed_rows)
    history=Path(c.read(folder/"AF_RESUME_HISTORY.json")["path"])
    run_day.protected_idle()
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in CPUS)
        status(operation="RUNNING_BOUNDED_CALM_EXTENSION", extension_source=str(cp), extension_steps=steps)
        result=job(FIXED,cp,t,source_af_history=history.as_posix(),af_branch_history=False,macro_source=FAST_MACRO,
                   matched_calm_fixed=True,fixed_window_seed=seed.as_posix(),fixed_elapsed_before=count,
                   fixed_stable_count=int(gate.get("stable_windows",0)),moving=False,
                   steps=steps,limit_seconds=min(10800,remaining()-2700))
        c.publish(result)
        status(calm_extension_result=result)
        return result
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


def run_wave_chain(fixed_result=None):
    proof = c.read(P / "RESIDUAL_CACHED_MACRO_SMOKE_20261105/SOLVE_STATUS.json")
    if not FAST_MACRO.is_file() or not verify_result({**proof,"transport_ok":True,"samples":proof.get("steps")},25):
        raise RuntimeError("Optimized diagnostic macro did not verify")
    status(residual_monitor_strategy="Reuse exact sample counts; recheck every 25 steps",
           residual_cached_macro_sha256=c.sha(FAST_MACRO))
    if fixed_result is None:
        if "--after-pid" in sys.argv:
            owner = int(sys.argv[sys.argv.index("--after-pid")+1])
            if c.STOP.exists() or not c.LOCK.exists() or int(c.LOCK.read_text().strip()) != owner:
                raise RuntimeError("Expected timestep-screen owner of the existing Mini lock")
        else:
            active = c.read(P / "DAY_STATUS.json")
            if active["stage"] not in (FIXED, MOTION) or c.STOP.exists() or not c.LOCK.exists():
                raise RuntimeError("Expected existing CALM/motion production")
            owner = int(c.LOCK.read_text().strip())
        status(operation="WAITING_FOR_CALM_AND_NIGHT_WINDOW", waits_for_pid=owner,
               window="2026-11-05 21:00 to 2026-11-06 07:00 CET",
               cases=[FIXED_CASE, ACTIVE_CASE], dt_s=DT, cpu_indices=CPUS,
               U_m_s=18, wavelength_m=10, wave_height_m=.10, training_approved=False)
        wait_for_calm_and_motion(owner)
        while time.time() < START:
            if c.STOP.exists():
                raise RuntimeError("Stop marker observed")
            time.sleep(min(10, START-time.time()))
        prior = c.read(D / "CPU8_STATUS.json")
        fixed, motion = prior.get("fixed_result", {}), prior.get("motion_result", {})
        fixed = extend_calm(fixed)
    else:
        fixed, motion = fixed_result, {}
    if (fixed.get("status") != "PASS_CALM_FORCE_STABILIZATION"
            or fixed.get("stabilization", {}).get("stable_windows") != 3 or c.STOP.exists()):
        raise RuntimeError("CALM/FIXED has not passed its stabilization gate")
    cp = Path(fixed["checkpoint"])
    t = fixed["state"]["time_s"]
    if c.sha(cp) != fixed["checkpoint_sha256"]:
        raise RuntimeError("CALM checkpoint checksum mismatch")
    last = c.tail(cp.parent / "history.csv")[-1]
    if abs(float(last["delta_measured_deg"])) > 1e-10 or abs(float(last["time_s"])-t) > 1e-9:
        raise RuntimeError("Expected stabilized 0-degree source")
    history = Path(c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"])
    if not history.is_file():
        raise RuntimeError("Missing AF history")
    screened = c.read(screen.STATE)
    candidate = next((cfg for cfg in screen.CONFIGS[1:] if cfg[0] == screened.get("winner")), None)
    startup_target = WAVE_STARTUP_STEPS if candidate else 500
    budget = min(startup_target, int((remaining()-240) / 4.5))
    if budget < 500:
        status(operation="HOLD_NIGHT_BUDGET", next_case=FIXED_CASE)
        return
    run_day.protected_idle()
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in CPUS)
        origin = t
        status(operation="RUNNING_WAVE_STARTUP", wave_origin_s=origin, planned_steps=budget,
               source=str(cp), calm_screen_winner=screened.get("winner"))
        result = do_run(FIXED_CASE+"_STARTUP", cp, t, history, steps=budget,
                        amplitude=.05, old_amplitude=0, ramp_s=RAMP, ramp_origin_s=origin)
        status(startup_result=result)
        if not verify_result(result, budget):
            status(operation="HOLD_FIXED_STARTUP", next_case=FIXED_CASE)
            return
        if budget < startup_target:
            status(operation="PARTIAL_FIXED_STARTUP_BUDGET", next_case=FIXED_CASE,
                   restart_preserve_ramp_origin_s=origin)
            return
        if not candidate or remaining() < 1800:
            status(operation="HOLD_FASTER_SETTINGS_UNVERIFIED", next_case=FIXED_CASE)
            return
        cp = Path(result["checkpoint"])
        t = result["state"]["time_s"]
        if c.sha(cp) != result["checkpoint_sha256"]:
            raise RuntimeError("Wave startup checkpoint checksum mismatch")
        history = Path(c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"])
        wave_options = dict(calm_only=False, clean_calm=False, amplitude=.05, old_amplitude=.05)
        status(operation="WAVE_DT_QUALIFICATION", wave_checkpoint=str(cp), candidate=candidate)
        ref, r0 = screen.evaluate(screen.CONFIGS[0], cp, t, history, wave_options)
        alternates = [cfg for cfg in screen.CONFIGS[1:] if cfg[0] != candidate[0]
                      and screened.get("results",{}).get(cfg[0],{}).get("status") == "PASS"]
        alternates.sort(key=lambda cfg: screened["results"][cfg[0]]["wall_s_per_physical_s"])
        comparisons = []
        selected = None
        for option in [candidate] + alternates[:1]:
            if remaining() < 1200 or c.STOP.exists():
                break
            try:
                fast, rf = screen.evaluate(option, cp, t, history, wave_options,
                                           timeout=min(1000, remaining()))
                agree, differences = screen.compare(ref, fast)
                good = agree and rf["wall_s_per_physical_s"] < .95*r0["wall_s_per_physical_s"]
                comparisons.append({"config":option,"pass":good,"candidate":rf,"differences":differences})
                if good:
                    selected = option
                    break
            except (ValueError, RuntimeError, OSError, KeyError) as error:
                if c.STOP.exists():
                    raise
                run_day.protected_idle()
                comparisons.append({"config":option,"pass":False,"reason":str(error)})
        status(wave_comparison={"reference":r0,"attempts":comparisons})
        if selected is None:
            status(operation="HOLD_FASTER_SETTINGS_UNVERIFIED", next_case=FIXED_CASE)
            return
        candidate = selected
        _, dt, inner = candidate
        target_steps = math.ceil((origin+FIXED_DURATION-t)/dt - 1e-10)
        budget = min(target_steps, int((remaining()-240) / max(4, 1.15*rf["full_s_per_step"])))
        if budget < 25:
            status(operation="READY_FIXED_NEXT_WINDOW", next_case=FIXED_CASE)
            return
        status(operation="RUNNING_WAVE_FIXED", planned_steps=budget, fixed_target_steps=target_steps,
               selected_dt_s=dt, selected_inner=inner)
        result = do_run(FIXED_CASE, cp, t, history, steps=budget, dt=dt, inner=inner,
                        amplitude=.05, old_amplitude=.05)
        status(fixed_result=result)
        if not verify_result(result, budget):
            status(operation="HOLD_FIXED", next_case=FIXED_CASE)
            return
        if budget < target_steps:
            status(operation="PARTIAL_FIXED_BUDGET", next_case=FIXED_CASE,
                   resume_remaining_steps=target_steps-budget, restart_preserve_ramp_origin_s=origin)
            return
        cp = Path(result["checkpoint"])
        gate = fixed_gate(cp.parent, origin, dt)
        status(wave_gate=gate)
        if not gate["pass"]:
            status(operation="HOLD_WAVE_QUALITY", next_case=ACTIVE_CASE)
            return
        if not verify_result(motion, 2500):
            status(operation="HOLD_CALM_MOTION", next_case=ACTIVE_CASE)
            return
        if remaining() < 240 + ACTIVE_STEPS * 5.5:
            status(operation="READY_ACTIVE_NEXT_WINDOW", next_case=ACTIVE_CASE)
            return
        t = result["state"]["time_s"]
        history = Path(c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"])
        status(operation="RUNNING_ACTIVE_TWO_PULSES", next_case=ACTIVE_CASE, active_start_s=t)
        active_result = do_run(ACTIVE_CASE, cp, t, history, steps=ACTIVE_STEPS, moving=True,
                               amplitude=.05, old_amplitude=.05, flow_cycle=True,
                               flap_cycle_deg=2, flap_quarter_s=.10, calm_active_pilot=True)
        status(operation="REVIEW_SEED_TRAJECTORIES" if verify_result(active_result, ACTIVE_STEPS)
               else "HOLD_ACTIVE", active_result=active_result)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


def independent_motion():
    archive = P / "runs/MATCHED_FIXED_SHARP_SEALED_ACTIVE_1050_20261104_162018"
    source = archive / "input.sim"
    expected = "f509fe6f7d70b61b9d53177ce7d4cd1cb2cc1b2fc11b23fcc57fae136a06e527"
    if c.sha(source) != expected:
        raise RuntimeError("Independent stabilized single-phase source did not verify")
    trials = (("NIGHT_SP_SEALED_I12", 12, .05, 800), ("NIGHT_SP_SEALED_SLOW_PULSE", 20, .07, 1120))
    run_day.protected_idle()
    prior_operation = ST.get("operation")
    with c.LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK=c.coex.MASK=sum(1<<n for n in CPUS)
        results = {}
        for name, inner, quarter, steps in trials:
            if remaining() < 240+5*steps or c.STOP.exists():
                break
            status(operation="RUNNING_INDEPENDENT_MOTION", primary_wave_status=prior_operation,
                   independent_case=name, independent_results=results)
            try:
                result = run_day.new_job(name,
                    dict(source=source, expected_cells=17462, stokes=True, foil=True, moving=True,
                         single_phase=True, coarse_2d_active=True, flow_cycle=True, dt=.00025,
                         inner=inner, amplitude=0, old_amplitude=0, expected_time=1.05,
                         motion_origin_s=1.05, u_diagnostic_m_s=18, steps=steps, seeded_single_phase=True,
                         fixed_from_unsteady=True, flap_quarter_s=quarter, limit_seconds=min(remaining(),240+6*steps)),
                    protection=c.NightGuard(None,1.777749),
                    macro_source=archive/"MiniVofStokes.java", mpi_cpu_indices=CPUS)
                dest=c.publish(result)
                folder=Path(result["checkpoint"]).parent
                for f in ("single_phase.csv","residual_per_step.csv"):
                    if (folder/f).is_file():
                        c.archive(folder/f,dest/f)
                rows=c.tail(folder/"single_phase.csv")
                full=(result["status"]=="PASS_DIAGNOSTIC_SMOKE" and result["transport_ok"]
                      and result["samples"]==steps
                      and min(float(row["delta_measured_deg"]) for row in rows)<-1.99
                      and max(float(row["delta_measured_deg"]) for row in rows)>1.99)
                results[name]={"status":"DIAGNOSTIC_COMPLETE" if full else "HOLD","result":result,
                               "training_approved":False}
            except (ValueError,RuntimeError,OSError,KeyError) as error:
                if c.STOP.exists():
                    raise
                run_day.protected_idle()
                results[name]={"status":"HOLD","reason":str(error)}
            status(independent_results=results)
        status(operation="NIGHT_INDEPENDENT_REVIEW" if results else prior_operation,
               primary_wave_status=prior_operation,independent_results=results)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    try:
        try:
            run_wave_chain()
        except (ValueError,RuntimeError,OSError,KeyError) as error:
            status(operation="HOLD",reason=str(error))
        if (ST.get("operation","").startswith("HOLD") and not c.STOP.exists()
                and remaining() > 4240):
            independent_motion()
    except Exception as error:
        status(operation="HOLD",reason=str(error))
        raise
