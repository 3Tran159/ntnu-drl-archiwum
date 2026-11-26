from pathlib import Path
import csv
import json
import os
import sys
import time

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, new_job, sha
from run_recovery_calm_komega import protect_w06


def main():
    audit = json.loads((OUT/"MESH_AUDIT.json").read_text())
    mesh = OUT/"mesh_2d.msh"
    macro = OUT/"MiniVofStokes.java"
    output = OUT/"RESULT.json"
    if STOP.exists() or output.exists() or sha(mesh) != audit["mesh_sha256"]:
        raise RuntimeError("Gapped-flap test preflight blocked")
    with LOCK.open("x", encoding="ascii") as f:
        f.write(str(os.getpid()))
    results = {"status":"RUNNING"}
    try:
        common = dict(stokes=True, foil=True, moving=True, single_phase=True,
            coarse_2d_active=True, flow_cycle=True, expected_cells=audit["cells"],
            expected_time=0, amplitude=0, old_amplitude=0, inner=20, u_diagnostic_m_s=18,
            target_ambient_turbulence=True, limit_seconds=2100)
        for tag, settings in (
            ("BASELINE",dict(fresh=True,gap_baseline_only=True,dt=.0005,steps=0,
                             steady_ramp_iterations=200,u_initial_m_s=.10,steady_max_iterations=1550,
                             mesh_override=mesh.as_posix(),mesh_override_sha256=audit["mesh_sha256"])),
            ("DT050MS",dict(seeded_single_phase=True, dt=.0005, steps=400)),
            ("DT100MS",dict(seeded_single_phase=True, dt=.001, steps=200)),
        ):
            if STOP.exists():
                raise RuntimeError("Mini STOP requested")
            if tag != "BASELINE":
                settings["source"] = Path(results["BASELINE"]["checkpoint"])
                if sha(settings["source"]) != results["BASELINE"]["checkpoint_sha256"]:
                    raise RuntimeError("Baseline hash mismatch")
            results.update(stage=tag)
            coex.save(output, results)
            stamp = time.strftime("%H%M%S")
            guard = protect_w06("ACTIVE_GAP25_TIP_RELIEF_" + tag + "_" + stamp)
            result = new_job("ACTIVE_GAP25_TIP_RELIEF_" + tag, {**common, **settings}, protection=guard, macro_source=macro)
            result["W06"] = dict(baseline_s=guard.baseline,peak_slowdown=guard.peak,stop=guard.stopped) if guard else None
            results[tag] = result
            folder = Path(result["checkpoint"]).parent
            hist = folder/"single_phase.csv"
            if hist.exists() and tag != "BASELINE":
                with hist.open() as f:
                    rows = list(csv.DictReader(f))
                angles = [float(r["delta_measured_deg"]) for r in rows if "delta_measured_deg" in r]
                result["full_cycle"] = (result["transport_ok"] and result["status"]=="PASS_DIAGNOSTIC_SMOKE"
                    and len(angles)==settings["steps"] and min(angles)<-1.99 and max(angles)>1.99
                    and abs(angles[-1])<.01)
            coex.save(output, results)
            if (tag=="BASELINE" and (result["status"]!="GAP_BASELINE_READY" or not result["transport_ok"])
                or tag!="BASELINE" and not result["full_cycle"]):
                results["status"] = "HOLD"
                break
        else:
            results["status"] = "PASS_EXPLORATORY_FULL_CYCLES"
    except Exception as exc:
        results.update(status="HOLD",error=str(exc))
        raise
    finally:
        coex.save(output, results)
        LOCK.unlink()


if __name__=="__main__":
    main()


