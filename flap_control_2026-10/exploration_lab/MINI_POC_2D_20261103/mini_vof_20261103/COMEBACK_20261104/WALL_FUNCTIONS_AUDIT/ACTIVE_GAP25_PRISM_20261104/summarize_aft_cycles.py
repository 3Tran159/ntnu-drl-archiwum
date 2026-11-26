from pathlib import Path
import csv
import json
import statistics
import sys
import numpy as np

OUT = Path(__file__).resolve().parent
REPORT = Path(sys.argv[1]) if len(sys.argv)>1 else OUT/"AFT_ONLY_PRESSURE_GATE"


def series(path):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]} if rows else {}


def ranges(data, name):
    return [float(data[name].min()), float(data[name].max())]


def native_wall_statistics(folder):
    result = {}
    for path in sorted(folder.glob("yplus_*.csv")):
        with path.open() as f:
            reader = csv.reader(f)
            header = next(reader)
            index = next(i for i,n in enumerate(header) if "y+" in n.lower() or "yplus" in n.lower() or "wall y" in n.lower())
            rows = np.array([[float(c) for c in row] for row in reader])
        y = rows[:,index]
        result[path.stem] = dict(face_count=len(y), p10_p50_p90=np.percentile(y,[10,50,90]).tolist(),
                                 face_fraction_30_100=float(np.mean((y>=30)&(y<=100))))
    return result


def main():
    result = json.loads((REPORT/"RESULT.json").read_text())
    diagnostic=REPORT/"RESULT_DT0333MS.json"
    if diagnostic.exists():
        result.update(json.loads(diagnostic.read_text()))
    combined = {}
    metrics = {"status":result["status"]}
    for tag in ("DT050MS","DT100MS","DT0333MS"):
        run = result.get(tag)
        if not run:
            continue
        folder = Path(run["checkpoint"]).parent
        data = series(folder/"single_phase.csv")
        if not data:
            continue
        combined[tag] = data
        peak_cfl = int(data["max_CFL"].argmax())
        metrics[tag] = dict(full_cycle=run["full_cycle"], steps=len(data["time_s"]), end_s=float(data["time_s"][-1]),
            angle_deg=ranges(data,"delta_measured_deg"), CL=ranges(data,"CL"), CD=ranges(data,"CD"),
            hinge_moment_Nm_per_m=ranges(data,"Mh_Nm"), min_pABS_kPa=float(data["pABS_aft_cells_Pa"].min()/1000),
            min_pABS_on_walls_kPa=float(data["pABS_aft_wall_Pa"].min()/1000), max_CFL=float(data["max_CFL"][peak_cfl]),
            max_CFL_xy_m=[float(data[f"cfl_{axis}_m"][peak_cfl]) for axis in ("x","y")],
            min_volume=float(data["volume_min"].min()), min_face_validity=float(data["face_validity"].min()),
            min_quality=float(data["quality"].min()), max_mass_error_after_5=float(data["mass_relative"][5:].max()) if len(data["time_s"])>5 else None,
            min_flap_pABS_kPa=float(data["pflap_min_Pa"].min()/1000), min_flap_vapor_margin_kPa=float(data["flap_vapor_margin_Pa"].min()/1000), min_gap_pABS_kPa=float(data["pgap_min_Pa"].min()/1000), mean_solver_seconds=run["solver_step_mean_s"], W06=run["W06"], wall_yplus=native_wall_statistics(folder))
    if {"DT050MS","DT100MS"}<=combined.keys():
        a,b = (combined[tag] for tag in ("DT050MS","DT100MS"))
        mask = b["time_s"] <= a["time_s"][-1]+1e-10
        shared = b["time_s"][mask]
        if len(shared):
            metrics["matched_physical_times"] = {}
            for key in ("CL","CD","Mh_Nm","pABS_aft_cells_Pa","pABS_aft_wall_Pa"):
                error = b[key][mask]-np.interp(shared,a["time_s"],a[key])
                metrics["matched_physical_times"][key] = dict(n=len(error), max_abs=float(abs(error).max()),
                                                              rms=float(np.sqrt(np.mean(error**2))))
    (REPORT/"CYCLE_METRICS.json").write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))


if __name__=="__main__":
    main()


