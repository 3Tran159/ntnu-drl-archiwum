import csv
import math
import os
from pathlib import Path
import time

import numpy as np
import cpu8
import resume as r
from resume import c, D, P, CPUS, DT, FIXED, job, run_day

STATE = D / "TIMESTEP_SCREEN_STATUS.json"
PREVIOUS = P / "runs/CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE_20261105_180821"
STOP_TEXT = "Pause at a complete step for matched timestep and inner-iteration screening"
CONFIGS = (("REF", .0002, 20), ("DT04", .0004, 20), ("DT04_I12", .0004, 12),
           ("DT05_I12", .0005, 12))
DURATION = .016
LIMITS = {"CL": .0025, "CD": .01, "Mh": .01}
STATE_DATA = {}


def status(**items):
    STATE_DATA.update(items)
    c.coex.save(STATE, STATE_DATA)


def receipt(result, start, steps, dt):
    out = Path(result["checkpoint"]).parent
    if (result.get("status") != "NUMERICAL_END_PASS" or not result.get("transport_ok")
            or result.get("samples") != steps
            or abs(result["state"]["time_s"] - (start + steps*dt)) > 1e-9):
        raise ValueError(f"{result.get('status')}, {result.get('samples')} of {steps} steps")
    rows = c.tail(out / "history.csv")
    if len(rows) != steps or any(abs(float(x["time_s"]) - (start+(i+1)*dt)) > 1e-9
                               for i, x in enumerate(rows)):
        raise ValueError("Physical sample times inconsistent")
    elapsed = ((out / "RESIDUAL_FACTORS_END.json").stat().st_mtime -
               (out / "RESIDUAL_FACTORS_START.json").stat().st_mtime)
    read = lambda key: np.array([float(x[key]) for x in rows])
    fields = {key: read(key) for key in ("time_s", "CL", "CD", "Mh", "pflap", "pABSmin_Pa",
                                        "interface_CFL", "max_CFL", "mass_relative")}
    if not all(np.isfinite(x).all() for x in fields.values()):
        raise ValueError("Nonfinite performance observation")
    summary = dict(full_s_per_step=elapsed/steps, wall_s_per_physical_s=elapsed/(steps*dt),
                   solver_s_per_step=result["solver_step_median_s"], sample_count=steps,
                   max_interface_cfl=float(max(fields["interface_CFL"])),
                   max_cfl=float(max(fields["max_CFL"])), max_mass_relative=float(max(fields["mass_relative"])),
                   min_pabs_pa=float(min(fields["pABSmin_Pa"])), min_flap_pabs_pa=float(min(fields["pflap"])),
                   output=str(out))
    if out.name.startswith("WAVE_QUAL_"):
        probes = c.tail(out / "gauges.csv")
        for x in (-3.0, .952, 4.0):
            sample = [float(row["eta_actual_m"]) for row in probes if abs(float(row["x_m"])-x) < 1e-9]
            if len(sample) != steps or not np.isfinite(sample).all():
                raise ValueError("Missing wave gauge samples")
            fields[f"eta_{x}"] = np.array(sample)
    return fields, summary


def compare(reference, candidate):
    t = candidate["time_s"]
    if t[0] < reference["time_s"][0]-1e-9 or t[-1] > reference["time_s"][-1]+1e-9:
        raise ValueError("Candidate times outside reference")
    deltas = {}
    for k in LIMITS:
        base = np.interp(t, reference["time_s"], reference[k])
        deltas[k] = float(np.max(np.abs(candidate[k]-base))/max(float(np.max(np.abs(base))),1e-10))
    for k in ("pflap", "pABSmin_Pa"):
        base = np.interp(t, reference["time_s"], reference[k])
        deltas[k+"_max_pa"] = float(np.max(np.abs(candidate[k]-base)))
    equivalent = (all(deltas[k] <= limit for k,limit in LIMITS.items())
                  and max(deltas["pflap_max_pa"], deltas["pABSmin_Pa_max_pa"]) <= 1000)
    for key in (k for k in candidate if k.startswith("eta_")):
        base = np.interp(t, reference["time_s"], reference[key])
        deltas[key+"_max_m"] = float(np.max(np.abs(candidate[key]-base)))
        equivalent &= deltas[key+"_max_m"] <= .003
    return bool(equivalent), deltas


def evaluate(config, cp, t, history, wave_options=None, timeout=1000):
    label, dt, inner = config
    steps = round(DURATION/dt)
    settings = dict(dt=dt, inner=inner, source_af_history=history.as_posix(), af_branch_history=False,
                    moving=False, steps=steps, limit_seconds=timeout)
    if wave_options:
        settings.update(wave_options)
    prefix = "WAVE_QUAL" if wave_options else "CALM_QUAL"
    result = job(f"{prefix}_{label}", cp, t, **settings)
    fields, summary = receipt(result, t, steps, dt)
    summary.update(dt_s=dt, inner=inner, status="PASS", source_sha256=result["checkpoint_sha256_input"])
    return fields, summary


def main():
    day = c.read(P / "DAY_STATUS.json")
    if (Path(day["output"]) != PREVIOUS or day["solver_state"] != "RUNNING"
            or not c.LOCK.exists() or c.STOP.exists()):
        raise RuntimeError("Expected CALM/FIXED production")
    owner = int(c.LOCK.read_text().strip())
    with c.STOP.open("x", encoding="ascii") as stop:
        stop.write(STOP_TEXT)
    status(operation="CHECKPOINTING_PRODUCTION", owner=owner)
    until = time.monotonic() + 180
    while c.LOCK.exists() and time.monotonic() < until:
        time.sleep(3)
    run_day.protected_idle()
    if c.LOCK.exists() or c.STOP.read_text() != STOP_TEXT:
        raise RuntimeError("Production shutdown not verified")
    day = c.read(P / "DAY_STATUS.json")
    saved = c.read(PREVIOUS / "DAY_RESULT.json")
    cp = Path(saved["checkpoint"])
    t = saved["state"]["time_s"]
    if (Path(day["output"]) != PREVIOUS or day["solver_state"] != "STOPPED"
            or saved["status"] != "HOLD_STOP_OR_DEADLINE" or not saved["transport_ok"]
            or c.sha(cp) != saved["checkpoint_sha256"]):
        raise RuntimeError("Production checkpoint verification failed")
    hist_path = Path(c.read(PREVIOUS / "AF_RESUME_HISTORY.json")["path"])
    siblings = [r.SOURCE_RUN] + [P / "runs" / f"{FIXED}_{tag}"
                              for tag in ("20261105_173753", "20261105_175018", "20261105_180821")]
    rows = [row for run in siblings for row in c.tail(run / "history.csv")]
    total = 501 + len(rows)
    seed_rows = rows[-(250 + total % 250):]
    for i, row in enumerate(seed_rows):
        if (abs(float(row["time_s"]) - (t - (len(seed_rows)-1-i)*DT)) > 1e-9
                or abs(float(row["delta_measured_deg"])) > 1e-10):
            raise RuntimeError("Production force seed is not aligned")
    seed = D / "FIXED_SEED_AFTER_TIMESTEP_SCREEN.csv"
    with seed.open("x", newline="") as f:
        w = csv.DictWriter(f, ("time_s", "CL", "CD"), extrasaction="ignore")
        w.writeheader()
        w.writerows(seed_rows)
    gate = c.read(PREVIOUS / "CALM_FIXED_PROGRESS.json")
    with c.LOCK.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        c.STOP.rename(D / "STOP_FOR_TIMESTEP_SCREEN_ARCHIVED")
        c.local.night_flap.MASK = c.coex.MASK = sum(1 << n for n in CPUS)
        results = {}
        reference = None
        for cfg in CONFIGS:
            name = cfg[0]
            status(operation="SCREENING_CALM", case=name, checkpoint=str(cp), time_s=t, results=results)
            try:
                fields, summary = evaluate(cfg, cp, t, hist_path)
                if reference is None:
                    reference = fields
                else:
                    valid, differences = compare(reference, fields)
                    summary.update(status="PASS" if valid else "HOLD_EQUIVALENCE", differences=differences)
                results[name] = summary
            except (ValueError, RuntimeError, OSError, KeyError) as error:
                run_day.protected_idle()
                if c.STOP.exists():
                    raise
                results[name] = {"status": "HOLD", "reason": str(error)}
                if name == "REF":
                    break
        eligible = [(name, m) for name,m in results.items() if m["status"] == "PASS"]
        winner = min(eligible, key=lambda item: item[1]["wall_s_per_physical_s"])[0] if eligible else None
        status(operation="PRODUCTION_FIXED", results=results, winner=winner,
               selected_for_production=False, wave_recheck_required=True)
        cpu8.state.update(c.read(cpu8.STATE))
        cpu8.state.pop("reason", None)
        cpu8.update(operation="PRODUCTION_FIXED", selected_mpi=2, selected_cpu_indices=CPUS,
                    production_checkpoint=str(cp), production_time_s=t)
        cpu8.production(cp, t, hist_path, seed, gate, total, CPUS)
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        status(operation="HOLD", reason=str(error))
        raise
