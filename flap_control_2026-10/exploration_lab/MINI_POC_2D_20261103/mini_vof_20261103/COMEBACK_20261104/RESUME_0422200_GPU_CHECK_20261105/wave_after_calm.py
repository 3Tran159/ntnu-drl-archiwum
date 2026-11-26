import csv
import ctypes
from ctypes import wintypes
import math
import os
from pathlib import Path
import time

from resume import c, D, P, CPUS, DT, FIXED, MOTION, job, run_day

STATE = D / "WAVE_AFTER_CALM_STATUS.json"
STAGE = "WAVE_FIXED_NATIVE_H010_RAMP_SMOKE"
RAMP_S = .456
STEPS = 500


def status(**items):
    c.coex.save(STATE, items)


def wait_for_calm_and_motion(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    owner = kernel.OpenProcess(0x00100000, False, pid)
    if not owner:
        raise OSError(ctypes.get_last_error(), "Unable to verify the existing controller")
    end = time.monotonic() + 12 * 3600
    try:
        while time.monotonic() < end:
            if c.STOP.exists():
                raise RuntimeError("Stop marker observed. Wave launch cancelled.")
            outcome = kernel.WaitForSingleObject(owner, 5000)
            if outcome == 0:
                return
            if outcome != 258:
                raise OSError(ctypes.get_last_error(), "Controller wait failed")
    finally:
        kernel.CloseHandle(owner)
    raise RuntimeError("CALM/motion wait budget reached")


def main():
    active = c.read(P / "DAY_STATUS.json")
    if (active["stage"] not in (FIXED, MOTION) or not c.LOCK.is_file() or c.STOP.exists()
            or active["solver_state"] not in ("RUNNING", "STOPPED")):
        raise RuntimeError("Expected existing native CALM/motion controller")
    pid = int(c.LOCK.read_text().strip())
    status(operation="WAITING_FOR_CALM_AND_MOTION", waits_for_pid=pid, stage=STAGE,
           wave="Fifth Order", height_m=.10, wavelength_m=10, U_m_s=18, flap_deg=0,
           ramp_s=RAMP_S, dt_s=DT, steps=STEPS, classification="STARTUP_DIAGNOSTIC")
    wait_for_calm_and_motion(pid)
    state = c.read(D / "CPU8_STATUS.json")
    fixed, motion = state.get("fixed_result", {}), state.get("motion_result", {})
    gate = fixed.get("stabilization", {})
    if (state["operation"] != "MOTION_FINISHED" or fixed.get("status") != "PASS_CALM_FORCE_STABILIZATION"
            or gate.get("stable_windows") != 3 or motion.get("status") != "NUMERICAL_END_PASS"
            or not motion.get("transport_ok") or motion.get("samples") != 2500 or c.STOP.exists()):
        raise RuntimeError("Existing CALM or motion gate did not pass")
    cp = Path(fixed["checkpoint"])
    t = fixed["state"]["time_s"]
    if c.sha(cp) != fixed["checkpoint_sha256"] or abs(t - gate["time_s"]) > 1e-9:
        raise RuntimeError("Invalid stabilized production checkpoint")
    last = c.tail(cp.parent / "history.csv")[-1]
    if abs(float(last["delta_measured_deg"])) > 1e-10 or abs(float(last["time_s"]) - t) > 1e-9:
        raise RuntimeError("Fixed checkpoint is not at 0 degrees")
    history = Path(c.read(cp.parent / "AF_RESUME_HISTORY.json")["path"])
    if not history.is_file():
        raise RuntimeError("Fixed checkpoint history missing")
    run_day.protected_idle()
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in CPUS)
        status(operation="RUNNING_WAVE_STARTUP_DIAGNOSTIC", stage=STAGE, checkpoint=str(cp), start_s=t)
        result = job(STAGE, cp, t, source_af_history=history.as_posix(), af_branch_history=False,
                     calm_only=False, clean_calm=False, matched_calm=False, from_calm=True, moving=False,
                     old_amplitude=0, amplitude=.05, ramp_s=RAMP_S, ramp_origin_s=t,
                     steps=STEPS, limit_seconds=4800)
        c.publish(result)
        native = Path(result["checkpoint"]).parent
        setup = c.read(native / "STOKES_READBACK.json")
        progress = c.tail(native / "history.csv")
        with (native / "gauges.csv").open(newline="") as f:
            gauges = sum(1 for row in csv.DictReader(f) if math.isfinite(float(row["eta_actual_m"])))
        complete = (result["status"] == "NUMERICAL_END_PASS" and result["transport_ok"]
                    and len(progress) == STEPS and gauges > 0 and setup["wave_type"] == "FifthOrderVofWave")
        status(operation="WAVE_STARTUP_DIAGNOSTIC_PASS" if complete else "HOLD_WAVE_STARTUP",
               stage=STAGE, classification="STARTUP_DIAGNOSTIC", run_result=result,
               setup=setup, finite_gauge_samples=gauges)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        status(operation="HOLD", stage=STAGE, reason=str(error))
        raise
