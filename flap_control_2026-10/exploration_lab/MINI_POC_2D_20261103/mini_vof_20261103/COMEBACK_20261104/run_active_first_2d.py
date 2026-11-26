"""Full single-phase flap cycle, with an explicitly separate 10 m/s fallback."""
import csv
import json
import os
from pathlib import Path

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06

M=HERE/"WALL_FUNCTIONS_AUDIT"/"COARSE_FACETED_OPEN_CELLS"
mesh=M/"mesh_2d.msh"
audit=json.loads((M/"COARSE_AUDIT.json").read_text())
output=HERE/"ACTIVE_FIRST_2D_RESULT.json"
if STOP.exists() or output.exists() or audit["status"]!="OFFLINE_MESH_MOTION_PASS":
    raise RuntimeError("Active 2D preflight blocked")
with LOCK.open("x",encoding="ascii") as f:
    f.write(str(os.getpid()))
results={}
try:
    for u in (18,10):
        tag=f"ACTIVE_FIRST_2D_U{u}"
        guard=protect_w06(tag)
        run=new_job(tag,dict(stokes=True,fresh=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=audit["cells"],
            expected_time=0,amplitude=0,old_amplitude=0,dt=.001,inner=20,steps=200,
            u_diagnostic_m_s=u,target_ambient_turbulence=True,
            mesh_override=mesh.as_posix(),mesh_override_sha256=sha(mesh),limit_seconds=900),protection=guard)
        folder=Path(run["checkpoint"]).parent
        with (folder/"single_phase.csv").open() as f:
            rows=list(csv.DictReader(f))
        angles=[float(row["delta_measured_deg"]) for row in rows]
        full=(run["status"]=="PASS_DIAGNOSTIC_SMOKE" and run["transport_ok"] and len(rows)==200
            and min(angles)<-1.99 and max(angles)>1.99 and abs(angles[-1])<.01)
        results[str(u)]=dict(result=run,full_cycle=full,min_deg=min(angles,default=None),
            max_deg=max(angles,default=None),W06_peak=guard.peak if guard else None,
            W06_stop=guard.stopped if guard else None)
        coex.save(output,results)
        if full or STOP.exists() or run["status"] not in ("HOLD_STEADY_PRESSURE","HOLD_SINGLE_PHASE_SAFETY","HOLD_STEADY_NOT_SETTLED","HOLD_STEADY_MESH_OR_TURBULENCE"):
            break
except Exception as exc:
    coex.save(output,{**results,"status":"HOLD","error":str(exc)})
    raise
finally:
    LOCK.unlink()

