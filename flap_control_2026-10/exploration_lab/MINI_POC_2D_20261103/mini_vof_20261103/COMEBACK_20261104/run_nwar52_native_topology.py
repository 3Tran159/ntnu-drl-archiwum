import json
import os
from pathlib import Path
import shutil

import stokes_coexistence as coex
from run_day import HERE,ROOT,LOCK,STOP,new_job,sha
from run_recovery_calm_komega import protect_w06

base=ROOT/"MINI_NWAR_50K_20261104"
audit=json.loads((base/"MESH_CANDIDATE_02"/"NWAR_MESH_AUDIT.json").read_text())
proof=next((HERE/"runs").glob("ACTIVE_FIRST_2D_U18_RESUME_*/COMBINED_CYCLE/SOLVE_STATUS.json"))
assert json.loads(proof.read_text())["status"]=="PASS_EXPLORATORY_FULL_CYCLE"
mesh=Path(audit["native_mesh"])
assert sha(mesh)==audit["mesh_sha256"] and audit["within_target"] and not STOP.exists()
with LOCK.open("x",encoding="ascii") as f:f.write(str(os.getpid()))
try:
    guard=protect_w06("NWAR52_NATIVE_TOPOLOGY")
    job=new_job("NWAR52_NATIVE_TOPOLOGY",dict(verify=True,nwar_mesh_file=mesh.as_posix(),
        expected_cells=audit["cells"],steps=0,limit_seconds=580),protection=guard)
    out=Path(job["run_directory"])
    native=json.loads((out/"REOPEN.json").read_text())
    if native["pass"]:
        src=out/"NWAR_MESH_ONLY.sim"
        dst=base/"NWAR_52352_MESH_ONLY.sim"
        if dst.exists():raise FileExistsError(dst)
        shutil.copy2(src,dst)
        if sha(dst)!=sha(src):raise RuntimeError("Native mesh copy SHA mismatch")
        native.update(checkpoint=str(dst),checkpoint_sha256=sha(dst))
    coex.save(base/"NWAR_NATIVE_IMPORT.json",dict(result=native,run_directory=str(out),
        W06_peak=guard.peak if guard else None,C01_physics_attached=False,quasi2d_motion_tested=False))
finally:
    LOCK.unlink()


