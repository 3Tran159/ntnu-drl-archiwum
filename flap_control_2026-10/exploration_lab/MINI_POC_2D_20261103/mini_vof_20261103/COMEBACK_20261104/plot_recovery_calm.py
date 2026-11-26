"""Plot solver data from the flat-water recovery smoke test."""
from pathlib import Path
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summarize_h010 import get

folder=Path(sys.argv[1])
rows=get(folder/"history.csv")
if not rows:
    raise ValueError("No solved timesteps")
meta=json.loads((folder/"SOLVE_STATUS.json").read_text())
fig, axes=plt.subplots(3,2,sharex=True,figsize=(10,7),layout="constrained")
t=[1000*float(row["time_s"]) for row in rows]
curves=(("CL", "CL [-]", 1),("CD", "CD [-]", 1),
        ("Mh_per_m", "Mh [N m/m]", 1),("pABSmin_Pa", "Absolute pressure [kPa]", .001),
        ("max_CFL", "CFL [-]", 1),("mass_relative", "Relative mass error [-]", 1))
def add(ax,key,scale,label):
    ax.plot(t,[scale*float(row[key]) for row in rows],label=label,marker="." if len(t)<8 else None)
for ax,(key,label,scale) in zip(axes.flat,curves):
    add(ax,key,scale,{"pABSmin_Pa":"Domain","max_CFL":"Global"}.get(key,key))
    ax.set_ylabel(label);ax.grid(alpha=.25);ax.ticklabel_format(useOffset=False)
add(axes[1,1],"pbody",.001,"Foil")
axes[1,1].axhline(12.3392148,color="tab:red",ls="--",label="Pressure floor")
axes[1,1].legend(frameon=False)
add(axes[2,0],"interface_CFL",1,"Interface")
axes[2,0].legend(frameon=False)
for ax in axes[-1]: ax.set_xlabel("Physical time [ms]")
fig.suptitle("CALM/FIXED | local TE recovery | STAR-CCM+ 2606 | "+meta["status"])
fig.savefig(folder/"CALM_FIXED_ACTUAL.png",dpi=170)

