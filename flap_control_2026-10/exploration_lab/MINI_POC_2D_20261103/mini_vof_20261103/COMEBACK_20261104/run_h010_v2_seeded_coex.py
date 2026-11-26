"""Run the bounded H=0.10 m integration only while the independent queue is idle."""
import json
import os
from pathlib import Path
import time
import csv
import statistics

from run_day import HERE, LOCK, STOP, new_job, sha

FIXED_STEPS = 40
DT = .000025
V2 = HERE / "WALL_FUNCTIONS_AUDIT" / "HIGH_YPLUS_CANDIDATE_V2" / "Q2D" / "mesh_3d.msh"
V2_HASH = "fe27d868523c191bb33e02725257ee5e718976a7fec73ec06ff3fea7dbb3c8d4"
decision = HERE / "H010_V2_SEEDED_COEX_RESULT.json"
SEED = Path(r"F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\mini_vof_20261103\COMEBACK_20261104\runs\B_CFL_NATIVE_CELL_READBACK_20261104_095856\V2_FLOW_SEED.csv")

def record(payload):
    temp = decision.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf8")
    temp.replace(decision)

def fresh_w06_protection():
    import re
    import stokes_coexistence as coex
    from run_day import READ, query, independent_jobs

    coex.CASE = Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\runs\W06_20261104_100235_3b75bb")
    coex.W06_LAUNCHER = 12224
    coex.BASELINE_FILE = HERE/"H010_SEEDED_W06_RESUMED_BASELINE.json"
    coex.WATCH = HERE/"H010_SEEDED_W06_RESUMED_WATCH.csv"
    until = time.monotonic()+420
    while time.monotonic()<until:
        if independent_jobs() != [("W06","running")]:
            raise RuntimeError("Pinned W06 is no longer the only active independent job")
        try:
            data = coex.history()
            if data[-1][0] >= 75 and len(data)>=76:
                break
        except (FileNotFoundError, IndexError):
            pass
        time.sleep(5)
    else:
        raise RuntimeError("No fresh W06 baseline window")
    log=(coex.CASE/"star.log").read_text(encoding="utf8",errors="replace")
    ranks=re.findall(r"(?m)^Process rank 0\s+\S+\s+(\d+)\s*$",log)
    if len(set(ranks)) != 1:
        raise RuntimeError("W06 native rank not uniquely established")
    coex.RANK = int(ranks[0])
    coex.EXPECTED = {p["ProcessId"] for p in query(READ)
                     if "21.02.007-R8" in (p.get("ExecutablePath") or "")}
    if not {coex.RANK,coex.W06_LAUNCHER} <= coex.EXPECTED:
        raise RuntimeError("Pinned W06 process family missing")
    watcher=coex.W06Protection()
    watcher.make_baseline()
    watcher.preflight()
    with coex.WATCH.open("x",encoding="ascii",newline="") as stream:
        csv.writer(stream).writerow(("time","phase","w06_step","w06_physical_s",
            "w06_rolling_median_s","slowdown_fraction","mini_steps"))
    marker = HERE/"STOP_W06_RESUMED_STARTUP_20261104.txt"
    if (STOP.read_text(encoding="ascii").strip() != "Independent CFD appeared during startup"
            or marker.exists()):
        raise RuntimeError("Review own STOP before any restart")
    STOP.rename(marker)
    return watcher


if decision.exists():
    raise RuntimeError("Refuse to duplicate an existing integration attempt")
until = time.monotonic() + 300
while LOCK.exists() and not STOP.exists() and time.monotonic() < until:
    time.sleep(3)
with LOCK.open("x", encoding="ascii") as stream:
    stream.write(str(os.getpid()))
try:
    protection = fresh_w06_protection()
    common = dict(stokes=True, foil=True, amplitude=.05, old_amplitude=.05, dt=DT, inner=20)
    fixed = new_job("I1_H010_FIXED_V2_SEEDED_COEX",
        dict(common, fresh=True, expected_time=0, steps=FIXED_STEPS, mesh_override=V2.as_posix(),
             mesh_override_sha256=V2_HASH, flow_seed=SEED.as_posix(),
             flow_seed_sha256=sha(SEED), limit_seconds=720), protection=protection)
    payload = dict(fixed=fixed, active="HOLD", training_approved=False, night_approved=False)
    payload["W06"] = dict(baseline_s=protection.baseline,peak_slowdown=protection.peak,stop=protection.stopped)
    qualifies = fixed["status"] == "NUMERICAL_END_PASS"
    if fixed["status"] == "HOLD_RESIDUAL_WINDOW" and fixed["samples"] == FIXED_STEPS:
        root = Path(fixed["checkpoint"]).parent
        gate = json.loads((root/"RESIDUAL_FINAL25.json").read_text(encoding="utf8"))
        with (root/"residual_per_step.csv").open(encoding="utf8") as stream:
            reductions = [float(row["reduction"]) for row in csv.DictReader(stream)
                          if row["monitor"]=="Continuity"][-25:]
        qualifies = (gate["count"] == 25 and len(reductions)==25
                     and statistics.median(reductions) <= 1
                     and all(value <= .01 for key,value in gate["maxima"].items()
                             if key!="Continuity"))
        payload["exploratory_continuity_only"] = qualifies
    if not (fixed["transport_ok"] and fixed["samples"] == FIXED_STEPS and qualifies):
        payload["reason"] = "I2 requires a complete safe fixed smoke and either a residual pass or isolated continuity with non-growing inner median."
        record(payload)
    else:
        src = Path(fixed["checkpoint"])
        if sha(src) != fixed["checkpoint_sha256"]:
            raise RuntimeError("I1 checkpoint hash mismatch")
        payload["active"] = "PREFLIGHT"
        record(payload)
        payload["active"] = new_job("I2_H010_ACTIVE_V2_SEEDED_COEX",
            dict(common, source=src, expected_time=fixed["state"]["time_s"], moving=True,
                 steps=100, motion_ramp_s=.025, control_phase_rad=.97, limit_seconds=900), protection=protection)
        record(payload)
except Exception as exc:
    payload = locals().get("payload", {"fixed": "HOLD", "active": "HOLD"})
    record(dict(payload, error=str(exc)))
    raise
finally:
    LOCK.unlink()





