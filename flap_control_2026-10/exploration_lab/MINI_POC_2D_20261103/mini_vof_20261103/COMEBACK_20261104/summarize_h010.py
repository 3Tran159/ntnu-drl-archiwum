"""Postprocess only actual H=0.10 m solver exports."""
import csv
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent

def get(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def field(path):
    records = get(path)
    names = list(records[0])
    data = np.array([[float(r[n]) for n in names] for r in records])
    return names, data

def col(names, prefix):
    return next(i for i, name in enumerate(names) if name.startswith(prefix))

def wave_balance(out):
    names, a = field(out/"field_start.csv")
    names_b, b = field(out/"field_end.csv")
    xyz = [col(names, f"{axis} (") for axis in "XYZ"]
    if names != names_b or not np.array_equal(a[:, xyz], b[:, xyz]):
        raise ValueError("Non-matching start/end cell coordinates")
    volume = b[:, col(names, "Volume (")]
    answer = {}
    for key in ("Absolute Pressure", "Velocity[i]", "Velocity[j]", "Volume Fraction"):
        j = col(names, key)
        delta = b[:, j]-a[:, j]
        answer[key] = {"max_absolute_change": float(np.max(np.abs(delta))),
            "volume_weighted_rms_change": float(np.sqrt(np.average(delta**2, weights=volume))),
            "final_min": float(np.min(b[:,j])), "final_max": float(np.max(b[:,j]))}
    return answer

def peak(out, file="field_end.csv"):
    names, data = field(out/file)
    index = col(names, "Convective Courant Number")
    row = data[np.nanargmax(data[:,index])]
    return dict(zip(names, row.tolist()))

def plot(out, active=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    runs = [(out, "I1 fixed")]
    if active:
        runs.append((active, "I2 active"))
    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(9.2,8.7), layout="constrained")
    columns = ("delta_measured_deg", "CL", "CD", "Mh_per_m")
    for run,label in runs:
        rows = get(run/"history.csv")
        if not rows:
            continue
        t = [1000*float(r["time_s"]) for r in rows]
        eta = [r for r in get(run/"gauges.csv") if abs(float(r["x_m"])-.952)<1e-7]
        points = dict(linestyle="-", marker="." if len(rows)<8 else None, markersize=6, linewidth=1.5)
        axes[0].plot([1000*float(r["time_s"]) for r in eta],
                     [1000*float(r["eta_actual_m"]) for r in eta],label=label,**points)
        for ax,key in zip(axes[1:],columns):
            ax.plot(t,[float(r[key]) for r in rows],label=label,**points)
    for ax,label in zip(axes,("eta [mm]", "delta [deg]", "CL [-]", "CD [-]", "Mh [N m/m]")):
        ax.set_ylabel(label); ax.grid(alpha=.28); ax.ticklabel_format(useOffset=False)
    axes[0].legend(frameon=False)
    axes[-1].set_xlabel("Physical time [ms]")
    states = " / ".join(json.loads((run/"SOLVE_STATUS.json").read_text())["status"] for run,_ in runs)
    fig.suptitle(f"Mini-URANS VOF | Stokes V | H = 0.10 m | V2\nDiagnostic STAR-CCM+ histories | {states}")
    fig.savefig(out/"H010_INTEGRATION_ACTUAL.png", dpi=180)

if __name__ == "__main__":
    mode, folder = sys.argv[1:3]
    out = Path(folder)
    if mode == "balance":
        print(json.dumps(wave_balance(out),indent=2))
    elif mode == "plot":
        plot(out, Path(sys.argv[3]) if len(sys.argv)>3 else None)
        print(json.dumps(peak(out),indent=2))


