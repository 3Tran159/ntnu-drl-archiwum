from pathlib import Path
import json
import os
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import LOCK, STOP, independent_jobs, new_job, protected_idle, sha
from run_recovery_calm_komega import protect_w06

def main():
    output=OUT/"RESUME_RESULT.json"
    original=json.loads((OUT/"RESULT.json").read_text())["SHARP_SEALED"]
    resume=Path(original["checkpoint"])
    if (output.exists() or LOCK.exists() or not STOP.exists()
        or STOP.read_text().strip()!=original["W06"]["stop"]
        or not original["W06"]["stop"].startswith("W06 seven-step median slower")
        or original["fixed"] is not None or sha(resume)!=original["checkpoint_sha256"]):
        raise RuntimeError("Resume preflight blocked")
    if independent_jobs() not in ([], [("W06","running")]):
        raise RuntimeError("Unexpected independent queue state")
    sharp=ROOT/"SEALED_SHARP_MATCHED_OUTER"
    gapped=ROOT/"SEALED_OUTER_MESH_GAPPED"
    audit=lambda p:json.loads((p/"MESH_AUDIT.json").read_text())
    sa,ga=audit(sharp),audit(gapped)
    mesh=sharp/"mesh_2d.msh"
    gap=json.loads((gapped/"RESULT.json").read_text())["BASELINE"]
    source=Path(gap["checkpoint"])
    if sha(mesh)!=sa["mesh_sha256"] or sha(source)!=gap["checkpoint_sha256"] or gap["status"]!="GAP_BASELINE_READY":
        raise RuntimeError("Reference audit mismatch")
    with LOCK.open("x",encoding="ascii") as f:
        f.write(str(os.getpid()))
    results={"status":"RUNNING","comparison_gate":"min 0.2 s, 0.05 s windows, 3 consecutive, CL and CD drift <0.5%"}
    try:
        saved_stop=OUT/"STOP_W06_SLOWDOWN_ARCHIVED.txt"
        if saved_stop.exists():
            raise RuntimeError("W06 stop marker already archived")
        first_guard=protect_w06("MATCHED_FIXED_SHARP_SEALED_RETRY_"+time.strftime("%H%M%S"))
        if first_guard and first_guard.baseline>1.7279357*1.15:
            raise RuntimeError("W06 has not returned below its pre-retry slowdown limit")
        STOP.rename(saved_stop)
        common=dict(stokes=True,foil=True,moving=True,single_phase=True,coarse_2d_active=True,flow_cycle=True,
                    expected_time=0,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,dt=.2/600,
                    target_ambient_turbulence=True,fixed_protocol=True,limit_seconds=5600)
        for name,settings in (
            ("SHARP_SEALED",dict(source=resume,seeded_single_phase=True,gap_resume_steady=True,
                expected_cells=sa["cells"],steady_max_iterations=1550,steps=600,after_fixed_motion=True)),
            ("GAP",dict(source=source,seeded_single_phase=True,gapped_geometry=True,after_fixed_motion=True,expected_cells=ga["cells"],steps=600)),
        ):
            if STOP.exists():
                raise RuntimeError("Mini STOP requested")
            results["stage"]=name
            coex.save(output,results)
            guard=first_guard if name=="SHARP_SEALED" else protect_w06("MATCHED_FIXED_"+name+"_"+time.strftime("%H%M%S"))
            result=new_job("MATCHED_FIXED_"+name,{**common,**settings},protection=guard,macro_source=OUT/"MiniVofStokes.java")
            path=Path(result["checkpoint"]).parent/"FIXED_PROTOCOL.json"
            result["fixed"]=json.loads(path.read_text()) if path.exists() else None
            result["W06"]=dict(peak=guard.peak,stop=guard.stopped) if guard else None
            results[name]=result
            coex.save(output,results)
        ok=all((results[k]["fixed"] or {}).get("status")=="PASS_FIXED_STABILIZATION" for k in ("SHARP_SEALED","GAP"))
        results["status"]="PASS_FIXED_PAIR" if ok else "HOLD_FIXED_PAIR"
    except Exception as exc:
        results.update(status="HOLD",error=str(exc))
        raise
    finally:
        coex.save(output,results)
        LOCK.unlink()

if __name__=="__main__":
    main()


