import json
from pathlib import Path
from run_day import HERE,LOCK,STOP,new_job,protected_idle,sha

p=HERE/"B_SEEDED_URANS_DT25US_SPRINT.json"
record=json.loads(p.read_text(encoding="utf8"))["result"]
src=Path(record["checkpoint"])
if record["status"]!="PASS_DIAGNOSTIC_SMOKE" or sha(src)!=record["checkpoint_sha256"]:
    raise RuntimeError("B checkpoint mismatch")
with LOCK.open("x",encoding="ascii") as f:
    import os
    f.write(str(os.getpid()))
try:
    protected_idle()
    result=new_job("B_CFL_NATIVE_READBACK",dict(source=src,verify=True,cfl_probe=True,steps=0,limit_seconds=540))
    (HERE/"B_CFL_NATIVE_READBACK_RESULT.json").write_text(json.dumps(result,indent=2),encoding="utf8")
finally:
    LOCK.unlink()

