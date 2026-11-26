from pathlib import Path
import time
import json
from run_day import HERE, LOCK, STOP, ROOT, sha
from run_sprint import run

name="B_SEEDED_SEALED_URANS"
deadline=time.monotonic()+760
while LOCK.exists() and not STOP.exists() and time.monotonic()<deadline:
    time.sleep(5)
if LOCK.exists() or STOP.exists() or not (HERE/"A_STOKES_CONTINUITY_DIAGNOSTIC_SPRINT.json").exists():
    raise RuntimeError("Wave diagnostic ownership or protection unresolved")
src=ROOT/"sealed0_fast_20261103"/"MINI_result.sim"
if sha(src)!="8433d57823ea06cb602675b82dea179241c59ed0b354ddac7e9c040e6a24c309":
    raise RuntimeError("Archived 2D checkpoint hash mismatch")
r=run(name,dict(source=src,stokes=True,foil=True,moving=True,single_phase=True,seeded_single_phase=True,
    expected_cells=14776,expected_time=0,amplitude=0,old_amplitude=0,dt=.0001,steps=50,
    motion_ramp_s=.003,control_phase_rad=-.5981592412434966,u_diagnostic_m_s=18,limit_seconds=660))
print(json.dumps(r,indent=2))

