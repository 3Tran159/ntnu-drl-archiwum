from pathlib import Path
import csv
import os
import sys

D=Path(__file__).resolve().parent
P=D.parents[1]
sys.path.insert(0,str(P/"FLAP_EXTREMA_VOF5_20261105/STABILIZE_FIRST"))
import run as c

SOURCE=Path("H:/NTNU_RESEARCH_ARCHIVE/Active Flaps/Sharp_Sealed_Native_Quasi2D_VOF_STAR2606_20261105/Sharp_Sealed_VOF_Native_Quasi2D.sim")
HASH="6f5251c7af1f1fa36750f8ec98749e99e79d5e4f40cf5359bfe6dfb73f4e1a9a"
MARKER="User requests native VOF mesh first. Graceful stop of owned fixed VOF only."
STAGE="CALM_VOF_NATIVE_SHARP_SEALED_FIXED_SMOKE30"
CPUS=[22,23]

def start():
    day=c.read(P/"DAY_STATUS.json")
    if day["solver_state"]!="STOPPED" or c.filtered_query(c.OWNER) or c.LOCK.exists():
        raise RuntimeError("Unexpected active Mini controller or solver")
    if c.sha(SOURCE).lower()!=HASH or c.STOP.exists() or (D/"OLD_IMPORTED_MESH_PAUSE_ARCHIVED.txt").read_text().strip()!=MARKER:
        raise RuntimeError("Native mesh source or known pause marker mismatched")
    with c.LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    try:
        mask=sum(1<<cpu for cpu in CPUS)
        c.local.night_flap.MASK=mask
        c.coex.MASK=mask
        c.coex.save(D/"STATUS.json",dict(status="RUNNING",stage=STAGE,source=str(SOURCE),steps_limit=30))
        result=c.new_job(STAGE,dict(source=SOURCE,expected_time=0,expected_cells=24515,stokes=True,
            foil=True,calm_only=True,clean_calm=True,matched_calm=True,moving=False,af_native=True,
            native_remesh_initialize=True,pressure_diagnostic_only=True,dt=.0002,inner=20,
            amplitude=0,old_amplitude=0,steps=30,save_interval_s=.005,limit_seconds=1800),
            protection=c.NightGuard(None,1.777749),macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=CPUS)
        out=Path(result["checkpoint"]).parent
        af=c.read(out/"AF_NATIVE_SAMPLES.json")
        init=c.read(out/"CLEAN_NATIVE_INITIALIZATION.json")
        frames=max(v for k,v in af["history_states"].items() if STAGE in k)
        ok=(result["samples"]==30 and result["transport_ok"] and result["status"] in
            ("NUMERICAL_END_PASS","HOLD_RESIDUAL_WINDOW") and init["pass"] and
            af["monitors"]["AF_CL Monitor"]["count"]>=25 and af["monitors"]["AF_CD Monitor"]["count"]>=25 and frames>=2)
        c.coex.save(D/"STATUS.json",dict(status="PASS_SMOKE_DIAGNOSTIC" if ok else "HOLD",
            stage=STAGE,result=result,AF_checkpoint=af,case=str(out)))
    except Exception as error:
        c.coex.save(D/"STATUS.json",dict(status="HOLD",stage=STAGE,reason=str(error)))
        raise
    finally:
        if not c.filtered_query(c.OWNER):
            c.LOCK.unlink()

if __name__=="__main__":
    start()

