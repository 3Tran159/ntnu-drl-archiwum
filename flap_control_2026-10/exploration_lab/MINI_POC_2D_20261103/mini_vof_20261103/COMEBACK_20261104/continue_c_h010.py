"""Gate the requested H=0.10 m integration smoke on completed native tests."""
import time
from pathlib import Path
import json

import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, sha
from run_sprint import run
from export_trajectory import export

STATE=HERE/"H010_INTEGRATION_STATUS.json"
WAVE=HERE/"A_STOKES_H010_QUAL40_SPRINT.json"
MOTION=HERE/"B_SEEDED_URANS_DT25US_SPRINT.json"

def update(**v):
    coex.save(STATE,{**v,"night_authorized":False})

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def passed(r):
    return r.get("transport_ok") and r.get("samples")==40 and r.get("status")=="NUMERICAL_END_PASS"

def main():
    if STATE.exists():
        raise RuntimeError("H010 integration gate already registered")
    update(operation="WAIT_H010_WAVE",status="BLOCKED")
    deadline=time.monotonic()+900
    while time.monotonic()<deadline and (LOCK.exists() or not WAVE.exists()) and not STOP.exists():
        time.sleep(6)
    if LOCK.exists() or STOP.exists() or not WAVE.exists():
        update(operation="HOLD",status="HOLD",reason="Prior wave/STOP or ownership")
        return
    a=read(WAVE).get("result",{})
    b=read(MOTION).get("result",{})
    if not passed(a) or b.get("status")!="PASS_DIAGNOSTIC_SMOKE":
        update(operation="HOLD",status="HOLD",reason="Native H010 wave or single-phase gate failed",wave=a,motion=b)
        return
    audit=read(HERE/"WALL_FUNCTIONS_AUDIT"/"HIGH_YPLUS_CANDIDATE_V2"/"CANDIDATE_AUDIT.json")
    mesh=Path(audit["native_import_file"])
    if audit["status"]!="OFFLINE_MESH_MOTION_PASS" or sha(mesh)!=audit["native_import_sha256"]:
        raise RuntimeError("Wall candidate mesh contract")
    update(operation="FIXED_DIAGNOSTIC",status="RUNNING")
    try:
        fixed=run("C_H010_FIXED_HIGH_YPLUS_SMOKE",dict(fresh=True,stokes=True,foil=True,expected_time=0,
            amplitude=.05,old_amplitude=.05,steps=40,dt=.000025,mesh_override=str(mesh),
            mesh_override_sha256=audit["native_import_sha256"],limit_seconds=720))
        if not passed(fixed):
            update(operation="HOLD",status="HOLD",reason="Fixed foil pilot failed",fixed=fixed)
            return
        cp=Path(fixed["checkpoint"])
        if sha(cp)!=fixed["checkpoint_sha256"]:
            raise RuntimeError("Fixed pilot checkpoint hash mismatch")
        update(operation="ACTIVE_DIAGNOSTIC",status="RUNNING",fixed=fixed)
        active=run("MINI_Q2D_STOKES5_ACTIVE_FLAP_H010",dict(source=cp,stokes=True,foil=True,moving=True,
            expected_time=fixed["state"]["time_s"],amplitude=.05,old_amplitude=.05,dt=.000025,
            motion_ramp_s=.003,control_phase_rad=-.5981592412434966,steps=40,limit_seconds=720))
        folder=Path(active["checkpoint"]).parent
        if active["samples"]:
            export(folder,folder/"DATASET_DIAGNOSTIC","DIAGNOSTIC","SEALED_Q2D_HIGH_YPLUS_V2_44442")
        update(operation="COMPLETE" if passed(active) else "HOLD",status="PASS_DIAGNOSTIC_SMOKE" if passed(active) else "HOLD",
               fixed=fixed,active=active,training_approved=False)
    except Exception as e:
        update(operation="HOLD",status="HOLD",reason=str(e))
        raise

if __name__=="__main__":
    main()

