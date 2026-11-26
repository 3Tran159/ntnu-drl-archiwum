"""Run the bounded H=0.10 m integration only while the independent queue is idle."""
import json
import os
from pathlib import Path
import time
import csv
import statistics

from run_day import HERE, LOCK, STOP, new_job, protected_idle, sha

FIXED_STEPS = 40
DT = .000025
V2 = HERE / "WALL_FUNCTIONS_AUDIT" / "HIGH_YPLUS_CANDIDATE_V2" / "Q2D" / "mesh_3d.msh"
V2_HASH = "fe27d868523c191bb33e02725257ee5e718976a7fec73ec06ff3fea7dbb3c8d4"
decision = HERE / "H010_V2_SEEDED_RESULT.json"
SEED = Path(r"F:\ntnu\flap_control\exploration_lab\MINI_POC_2D_20261103\mini_vof_20261103\COMEBACK_20261104\runs\B_CFL_NATIVE_CELL_READBACK_20261104_095856\V2_FLOW_SEED.csv")

def record(payload):
    temp = decision.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf8")
    temp.replace(decision)

if decision.exists():
    raise RuntimeError("Refuse to duplicate an existing integration attempt")
until = time.monotonic() + 300
while LOCK.exists() and not STOP.exists() and time.monotonic() < until:
    time.sleep(3)
protected_idle()
with LOCK.open("x", encoding="ascii") as stream:
    stream.write(str(os.getpid()))
try:
    common = dict(stokes=True, foil=True, amplitude=.05, old_amplitude=.05, dt=DT, inner=20)
    fixed = new_job("I1_H010_FIXED_V2_SEEDED",
        dict(common, fresh=True, expected_time=0, steps=FIXED_STEPS, mesh_override=V2.as_posix(),
             mesh_override_sha256=V2_HASH, flow_seed=SEED.as_posix(),
             flow_seed_sha256=sha(SEED), limit_seconds=720))
    payload = dict(fixed=fixed, active="HOLD", training_approved=False, night_approved=False)
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
        payload["active"] = new_job("I2_H010_ACTIVE_V2_SEEDED",
            dict(common, source=src, expected_time=fixed["state"]["time_s"], moving=True,
                 steps=100, motion_ramp_s=.003, control_phase_rad=.97, limit_seconds=900))
        record(payload)
except Exception as exc:
    payload = locals().get("payload", {"fixed": "HOLD", "active": "HOLD"})
    record(dict(payload, error=str(exc)))
    raise
finally:
    LOCK.unlink()



