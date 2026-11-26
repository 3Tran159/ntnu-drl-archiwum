"""Plot the measured pilot rollouts on the same XFOIL wave."""
import csv
import json
from pathlib import Path
import sys
import numpy as np

OUT = Path(__file__).resolve().parent
sys.path.append(str(OUT.parents[1] / "plot_deps_312"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def episode(name):
    with (OUT / (name + "_eval.csv")).open(newline="") as stream:
        rows=[r for r in csv.DictReader(stream) if float(r["episode"])==0]
    return np.array([[float(r[k]) for k in ("time_s","CL_vertical","CD_x","foil_pitch_deg")] for r in rows])


result=json.loads((OUT/"TD3_XFOIL_PILOT_RESULT.json").read_text())
fig,axes=plt.subplots(3,1,sharex=True,figsize=(8.4,7),layout="constrained")
for name,label,style,colour in (
        ("fixed_trim","Fixed pitch trim","--","#65737c"),
        ("xfoil_inverse","XFOIL inverse reference",":","#a64f16"),
        ("td3_pitch","TD3 pitch policy","-","#12657d")):
    data=episode(name)
    for i,ax in enumerate(axes,1):
        ax.plot(data[:,0]-data[0,0],data[:,i],style,label=label,color=colour,linewidth=1.7)
        ax.grid(alpha=.2)
axes[0].axhspan(*result["band_1pct"],color="#2e9f71",alpha=.12,label="±1% lift band")
axes[0].set_ylabel("Vertical lift coefficient")
axes[0].legend(frameon=False,ncol=2,loc="upper right",fontsize=8)
axes[1].set_ylabel("Axial drag coefficient")
axes[2].set_ylabel("Whole-foil pitch [deg]")
axes[2].set_xlabel("Time after discarded first cycle [s]")
fig.suptitle("TD3 pilot | Godø-equivalent mean lift on XFOIL",fontsize=15,fontweight="bold")
fig.savefig(OUT/"TD3_XFOIL_PILOT.png",dpi=175)
