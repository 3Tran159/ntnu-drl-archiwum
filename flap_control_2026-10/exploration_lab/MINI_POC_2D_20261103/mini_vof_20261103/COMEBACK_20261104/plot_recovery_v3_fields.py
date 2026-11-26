"""Plot the actual native Recovery V3 cell fields before/after the solver."""
from pathlib import Path
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from summarize_h010 import col, field

out = Path(sys.argv[1])
files = [out/"field_start.csv",out/"field_end.csv"]
fig, axes = plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True,layout="constrained")
frames=[]
for f in files:
    names,a=field(f)
    x,y=a[:,col(names,"X (")],a[:,col(names,"Y (")]
    q=a[:,[col(names,"Velocity["+i+"]") for i in "ijk"]]
    sel=(x>=-.22)&(x<=1.5)&(y>=-.28)&(y<=.32)
    frames.append((x[sel],y[sel],np.linalg.norm(q[sel],axis=1),a[sel,col(names,"Absolute Pressure")]/1000))
meta=json.loads((out/"SOLVE_STATUS.json").read_text())
for row,label in enumerate(("Speed [m/s]", "Absolute pressure [kPa]")):
    data=[r[2+row] for r in frames]
    norm=Normalize(min(v.min() for v in data),max(v.max() for v in data))
    for i,ax in enumerate(axes[row]):
        x,y=frames[i][:2]
        sc=ax.scatter(x,y,c=data[i],s=3,cmap=("viridis" if row==0 else "coolwarm"),norm=norm,rasterized=True)
        ax.set(aspect="equal",xlim=(-.22,1.5),ylim=(-.28,.32))
        ax.set_title(("Native initialization", f"After {meta['steps']} step(s) | {meta['status']}")[i])
    fig.colorbar(sc,ax=axes[row].tolist(),label=label,shrink=.8)
for ax in axes[-1]: ax.set_xlabel("x [m]")
for ax in axes[:,0]: ax.set_ylabel("y [m]")
case_name = "Clean native initialization" if out.name.startswith("CLEAN_NATIVE_") else "Warm start from C01"
fig.suptitle(f"CALM/FIXED | {case_name} | actual STAR fields")
fig.savefig(out/("CLEAN_NATIVE_FIELDS.png" if out.name.startswith("CLEAN_NATIVE_") else "RECOVERY_V3_NATIVE_FIELDS.png"),dpi=190)


