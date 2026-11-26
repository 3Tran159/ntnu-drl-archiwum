"""Overlay actual native wall vertices at measured flap extrema."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d=Path(sys.argv[1])
fig,axes=plt.subplots(2,1,figsize=(10,6),layout="constrained")
for file,label,col,marker in (("vertices_0000.csv","0 deg | initial","#587184","."),("vertices_step0050.csv","-2 deg | t = 0.05 s","#2283ad","o"),("vertices_step0150.csv","+2 deg | t = 0.15 s","#d17b49","o")):
    path=d/file
    if not path.exists():continue
    xy=np.loadtxt(path,delimiter=",",skiprows=1)[:,:2]
    for ax in axes:
        ax.scatter(*xy.T,s=9,marker=marker,alpha=.75,color=col,label=label)
for ax in axes:
    ax.axvline(.952,color="#777777",ls="--",lw=1)
    ax.grid(alpha=.3);ax.set_ylabel("y [m]")
axes[0].set(xlim=(-.02,1.23),ylim=(-.065,.13),aspect="equal")
axes[1].set(xlim=(.92,1.21),ylim=(-.028,.065),aspect="equal",xlabel="x [m]")
axes[0].legend(loc="upper right",frameon=False,ncols=3)
fig.suptitle("Actual STAR wall vertices with the URANS solver active")
fig.savefig(d/"ACTIVE_FLAP_NATIVE_EXTREMA.png",dpi=185)

