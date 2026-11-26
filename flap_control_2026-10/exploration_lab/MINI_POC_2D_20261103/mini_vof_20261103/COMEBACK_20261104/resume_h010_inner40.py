from pathlib import Path
import json
from run_day import HERE, sha
from run_sprint import run

proof=json.loads((HERE/"A_STOKES_H010_QUAL40_SPRINT.json").read_text(encoding="utf8"))["result"]
src=Path(proof["checkpoint"])
if proof["samples"]!=40 or proof["status"]!="HOLD_RESIDUAL_WINDOW" or sha(src)!=proof["checkpoint_sha256"]:
    raise RuntimeError("Unexpected H010 source")
g=json.loads((src.parent/"RESIDUAL_FINAL25.json").read_text(encoding="utf8"))
if [n for n,v in g["maxima"].items() if v>g["normalized_limit"]]!=["Continuity"]:
    raise RuntimeError("Continuity-only recovery is not applicable")
run("A_H010_INNER40",dict(source=src,stokes=True,foil=False,expected_time=.04,
    amplitude=.05,old_amplitude=.05,steps=40,inner=40,limit_seconds=720))

