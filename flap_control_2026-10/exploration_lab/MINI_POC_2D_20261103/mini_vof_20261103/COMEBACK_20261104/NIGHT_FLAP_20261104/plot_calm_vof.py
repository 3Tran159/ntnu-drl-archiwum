import csv
import json
from pathlib import Path
import sys

sys.path.insert(0,r"F:/ntnu/flap_control/exploration_lab/MINI_POC_2D_20261103/mini_vof_20261103/COMEBACK_20261104/WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104/plot_dependencies")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root=Path("T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104/NIGHT_FLAP_20261104")
summary=json.loads((root/"CALM_VOF_MATCHED_COMPARISON.json").read_text())
cases=[
    (("CALM_VOF_FIXED_SEALED_DT020_WMI_INTERRUPTED","CALM_VOF_FIXED_SEALED_DT020_WMI_RESUME"),"Sharp sealed","#576979","--"),
    (("CALM_VOF_FIXED_GAP_DT020",),"2.5 mm gap","#824378","-"),
]
fig,axes=plt.subplots(2,1,figsize=(9,5.7),sharex=True,layout="constrained")
for folders,label,color,style in cases:
    rows=[]
    for folder in folders:
        with (root/folder/"history.csv").open(newline="") as f:
            rows.extend(csv.DictReader(f))
    rows=[row for row in rows if float(row["time_s"]) > .0004+1e-12]
    time=[float(row["time_s"]) for row in rows]
    for ax,(key,ylabel) in zip(axes,[("CL","Buoyancy-corrected lift coefficient, $C_L$"),("CD","Drag coefficient, $C_D$")]):
        ax.plot(time,[float(row[key]) for row in rows],color=color,ls=style,lw=1.65,label=label)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=.22)
for ax in axes:
    ax.axvspan(summary["begin_s"],summary["end_s"],color="#c9d6a2",alpha=.4)
axes[0].legend(frameon=False)
axes[-1].set_xlabel("Physical time [s]")
fig.suptitle("Calm-water VOF | fixed flap at 0° | 18 m/s\nShaded region: common 50 ms window | first two startup steps in CSV")
fig.savefig(root/"calm_vof_force_histories_EN.png",dpi=185)


