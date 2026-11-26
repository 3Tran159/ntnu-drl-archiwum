import json,os
from pathlib import Path
from run_day import HERE,LOCK,STOP,new_job,sha
from run_recovery_calm_komega import protect_w06
c01=Path(r"E:\ntnu_mesh_optimization_20261030\clean_c01_campaign_20261101\C01_warm_M13_steady_rho1000_air1p2_20261101\final.sim")
expected="9af4857b948e0494088b5421f8ede100e66344fc2631cc00030406640d7cc295"
if STOP.exists() or sha(c01)!=expected:
    raise RuntimeError("C01 hash or Mini STOP preflight")
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
try:
    guard=protect_w06("RECOVERY_V3_C01")
    result=new_job("RECOVERY_V3_C01_READONLY",dict(source=c01,verify=True,c01_audit=True,steps=0,limit_seconds=580),protection=guard)
    if sha(c01)!=expected:
        raise RuntimeError("C01 original changed")
    (HERE/"RECOVERY_V3_C01_READBACK.json").write_text(json.dumps({**result,"original_sha256":expected,
        "w06_peak":guard.peak if guard else None},indent=2))
finally:
    LOCK.unlink()

