from pathlib import Path
import csv
from run_day import HERE, ROOT, sha
from run_sprint import run
old=next((HERE/"runs").glob("B_SEEDED_URANS_2D_QUALITY_*"))
with (old/"single_phase.csv").open() as f: h=list(csv.DictReader(f))
if len(h)!=1 or not (float(h[0]["max_CFL"])>25 and float(h[0]["pABSmin_Pa"])>12339.214766776897):
    raise RuntimeError("Not the verified CFL-limited restart")
src=ROOT/"sealed0_fast_20261103"/"MINI_result.sim"
if sha(src)!="8433d57823ea06cb602675b82dea179241c59ed0b354ddac7e9c040e6a24c309":
    raise RuntimeError("Seed SHA mismatch")
run("B_SEEDED_URANS_DT25US",dict(source=src,stokes=True,foil=True,moving=True,single_phase=True,
    seeded_single_phase=True,expected_cells=14776,expected_time=0,amplitude=0,old_amplitude=0,
    dt=.000025,steps=100,motion_ramp_s=.003,control_phase_rad=-.5981592412434966,
    u_diagnostic_m_s=18,limit_seconds=800))

