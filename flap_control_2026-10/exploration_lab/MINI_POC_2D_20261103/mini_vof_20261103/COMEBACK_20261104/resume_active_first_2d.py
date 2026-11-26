import csv
import json
import math
import os
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, READ, query, new_job, sha
from run_recovery_calm_komega import protect_w06

first=json.loads((HERE/"ACTIVE_FIRST_2D_RESULT.json").read_text())["18"]
run=first["result"]
cp=Path(run["checkpoint"])
archive=HERE/"STOP_ACTIVE_FIRST_GUI_20261104.txt"
result=HERE/"ACTIVE_FIRST_2D_RESUME_RESULT.json"
if (run["status"]!="HOLD_STOP_OR_DEADLINE" or run["samples"]!=143 or not run["transport_ok"]
        or sha(cp)!=run["checkpoint_sha256"] or result.exists()):
    raise RuntimeError("Active checkpoint failed restart contract")
with (cp.parent/"vertices_0000.csv").open() as f:
    rows=list(csv.reader(f))[1:]
    tip=max(((float(r[0]),float(r[1])) for r in rows if float(r[0])>=1.15),
            key=lambda q:math.hypot(q[0]-.952,q[1]-.02128173276777))
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
guard=None
try:
    guard=protect_w06("ACTIVE_FIRST_2D_RESUME")
    if not STOP.exists() or STOP.read_text().strip()!="Independent queue/process set changed" or archive.exists():
        raise RuntimeError("Unexpected Mini STOP marker")
    STOP.rename(archive)
    settings=dict(source=cp,stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,
        resume_coarse_active=True,flow_cycle=True,motion_origin_s=0,expected_cells=13597,
        expected_time=run["state"]["time_s"],amplitude=0,old_amplitude=0,dt=.001,inner=20,steps=57,
        reference_tip_x_m=tip[0],reference_tip_y_m=tip[1],u_diagnostic_m_s=18,limit_seconds=650)
    resumed=new_job("ACTIVE_FIRST_2D_U18_RESUME",settings,protection=guard)
    coex.save(result,dict(result=resumed,W06_peak=guard.peak if guard else None,W06_stop=guard.stopped if guard else None))
except Exception as exc:
    coex.save(result,dict(status="HOLD",error=str(exc),W06_stop=guard.stopped if guard else None))
    raise
finally:
    LOCK.unlink()

