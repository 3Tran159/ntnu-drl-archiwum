from pathlib import Path
import csv
import json
import sys

import numpy as np

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT/"plot_dependencies"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

SEALED = OUT.parents[1]/"runs/ACTIVE_FIRST_2D_U18_RESUME_20261104_115328/COMBINED_CYCLE"
HINGE = np.array([.952,.02128173276777])


def mesh_figure():
    data = np.load(OUT/"plot_mesh.npz")
    xy = data["xy"]
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), height_ratios=[1, 2.6, 2.6], layout="constrained")
    groups = ("triangles", "quads")
    for ax in axs:
        for group, color in zip(groups, ["#a3aeb8", "#2378a9"]):
            cells = data[group]
            segments = np.stack([xy[cells],xy[np.roll(cells,-1,axis=1)]],axis=2).reshape(-1,2,2)
            ax.add_collection(LineCollection(segments,colors=color,lw=.36,rasterized=True))
        for group in ("main", "flap"):
            ax.add_collection(LineCollection(xy[data[group]],colors="#152e41",lw=1))
        ax.set_aspect("equal")
        ax.set_ylabel("Vertical position [m]")
    axs[0].set(xlim=(-.03,1.23),ylim=(-.065,.118),title="Full foil and near-wall mesh")
    axs[1].set(xlim=(.902,1.010),ylim=(-.026,.064),title="Hinge and flap nose | nominal clearance 2.5 mm")
    axs[1].plot(*HINGE,"+",c="#a9482b",ms=9,mew=1.3)
    axs[2].set(xlim=(.913,.925),ylim=(.011,.032),title="Gap detail | three wall-layer rows on each side")
    axs[2].set_xlabel("Streamwise position [m]")
    meta=json.loads((OUT/"MESH_AUDIT.json").read_text())
    fig.suptitle(f'NACA 66-012 MOD | Gapped-flap mesh at 0° | {meta["cells"]:,} cells\n'
                 'Blue: wall-layer quadrilaterals   ·   Gray: core triangles',fontweight="bold")
    fig.savefig(OUT/"GAPPED_FLAP_MESH_EN.png",dpi=190)
    plt.close(fig)


def read_history(path):
    with path.open(newline="") as f:
        rows=list(csv.DictReader(f))
    return {k:np.array([float(r[k]) for r in rows]) for k in rows[0]} if rows else {}


def force_figure():
    result=json.loads((OUT/"RESULT.json").read_text())
    runs=[(read_history(SEALED/"single_phase.csv"),"Sealed prototype | 1.0 ms","#576979","--")]
    for key,dt,color in [("DT050MS","0.5","#127a92"),("DT100MS","1.0","#c56732")]:
        record=result.get(key)
        if record is None:
            continue
        path=Path(record["checkpoint"]).parent/"single_phase.csv"
        if not path.exists():
            continue
        series=read_history(path)
        if series:
            label=f"2.5 mm gap | {dt} ms"
            if not record.get("full_cycle"):
                label+=f' | partial ({series["time_s"][-1]:.3f} s)'
            runs.append((series,label,color,"-"))
    if len(runs)==1:
        return
    fig, axs = plt.subplots(2, 1, figsize=(8.7,7.4), sharex=True, layout="constrained")
    for ax,key,label in zip(axs,("CL","CD"),("Lift coefficient, $C_L$","Drag coefficient, $C_D$")):
        for series,name,color,style in runs:
            a=series["delta_measured_deg"]
            y=series[key]
            ax.plot(a,y,color=color,ls=style,label=name,lw=1.7)
            ax.scatter([a[0]],[y[0]],s=25,facecolors="white",edgecolors=color,zorder=5)
            ax.scatter([a[-1]],[y[-1]],s=25,color=color,zorder=5)
        ax.axvline(0,c="#a6a6a6",lw=.75)
        ax.grid(alpha=.2)
        ax.set_ylabel(label)
    axs[0].legend(frameon=False)
    axs[-1].set_xlabel("Measured flap deflection [deg] | positive = trailing edge down")
    fig.suptitle("Lift and drag during the flap cycle | 18 m/s\n"
                 "Open marker: first sample   ·   Filled marker: final sample\n"
                 "Sealed and gapped cases also differ in profile discretization and wall mesh")
    fig.savefig(OUT/"CL_CD_vs_flap_deflection_overlay_EN.png",dpi=190)
    plt.close(fig)


if __name__=="__main__":
    mesh_figure()
    if (OUT/"RESULT.json").exists():
        force_figure()


