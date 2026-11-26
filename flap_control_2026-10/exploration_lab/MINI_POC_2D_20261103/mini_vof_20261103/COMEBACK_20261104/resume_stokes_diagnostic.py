from pathlib import Path
import json
from run_day import HERE, sha
from run_sprint import run

proof=json.loads((HERE/"SPRINT_A_RAMP40_CFL_SAFE_SPRINT.json").read_text(encoding="utf8"))["result"]
src=Path(proof["checkpoint"])
if proof["samples"]!=40 or proof["status"]!="HOLD_RESIDUAL_WINDOW" or sha(src)!=proof["checkpoint_sha256"]:
    raise RuntimeError("Unexpected A checkpoint")
run("A_STOKES_CONTINUITY_DIAGNOSTIC",dict(source=src,stokes=True,expected_time=.04,
    amplitude=.25,old_amplitude=0,ramp_s=.9090748386259206,ramp_origin_s=0,steps=60,
    limit_seconds=720))

