from pathlib import Path
from run_day import HERE, ROOT, sha
from run_sprint import run
import json

old=next((HERE/"runs").glob("B_SEEDED_SEALED_URANS_*"))
d=json.loads((old/"ERROR.json").read_text(encoding="utf8"))
if d["steps"]!=1 or "NN_quality" not in d["error"]:
    raise RuntimeError("Refuse unqualified B retry")
src=ROOT/"sealed0_fast_20261103"/"MINI_result.sim"
if sha(src)!="8433d57823ea06cb602675b82dea179241c59ed0b354ddac7e9c040e6a24c309":
    raise RuntimeError("Seed SHA mismatch")
run("B_SEEDED_URANS_2D_QUALITY",dict(source=src,stokes=True,foil=True,moving=True,single_phase=True,
    seeded_single_phase=True,expected_cells=14776,expected_time=0,amplitude=0,old_amplitude=0,
    dt=.0001,steps=50,motion_ramp_s=.003,control_phase_rad=-.5981592412434966,u_diagnostic_m_s=18,limit_seconds=660))

