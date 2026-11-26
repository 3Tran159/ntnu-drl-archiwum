import csv
from pathlib import Path
import sys

sys.path.insert(0,r"F:/ntnu/flap_control/exploration_lab/MINI_POC_2D_20261103/mini_vof_20261103/COMEBACK_20261104/WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104/plot_dependencies")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root=Path("T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104")
out=root/"NIGHT_FLAP_20261104/GAP_PLUS_MINUS_2"
cases=[
    (root/"SHARP_SEALED_CYCLE_RESUME_1P064S/single_phase_combined.csv",1.05,"Sharp sealed","#576979","--"),
    (out/"cycle_full_available.csv",1.0,"2.5 mm gap","#824378","-"),
]
for mode in ("time","angle"):
    fig,axes=plt.subplots(3 if mode=="time" else 2,1,sharex=True,figsize=(9,7),layout="constrained")
    for file,origin,label,color,style in cases:
        with file.open(newline="") as f:
            rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
        x=[r["delta_measured_deg"] if mode=="angle" else 1000*(r["time_s"]-origin) for r in rows]
        fields=[("CL","Lift coefficient, $C_L$"),("CD","Drag coefficient, $C_D$")]
        if mode=="time":
            fields += [("pflap_min_Pa","Minimum flap pressure [kPa]")]
        for ax,(key,ylabel) in zip(axes,fields):
            values=[r[key]/1000 if key.endswith("_Pa") else r[key] for r in rows]
            ax.plot(x,values,color=color,ls=style,lw=1.6,label=label)
            ax.set_ylabel(ylabel)
            ax.grid(alpha=.22)
            if mode=="angle":
                ax.scatter(x[0],values[0],s=22,facecolor="white",edgecolor=color,zorder=4)
                ax.scatter(x[-1],values[-1],s=22,facecolor=color,zorder=4)
    axes[0].legend(frameon=False)
    if mode=="time":
        axes[-1].axhline(2.3392147668,color="#a64f36",ls=":",lw=1.2,label="Vapor pressure at 20 °C")
        axes[-1].legend(frameon=False)
    axes[-1].set_xlabel("Time since motion onset [ms]" if mode=="time" else "Measured flap deflection [deg] | positive = trailing edge down")
    fig.suptitle("Complete ±2° cycle | 18 m/s | matched outer mesh")
    fig.savefig(out/("complete_cycle_time_EN.png" if mode=="time" else "complete_cycle_CL_CD_vs_deflection_EN.png"),dpi=185)
    plt.close(fig)

