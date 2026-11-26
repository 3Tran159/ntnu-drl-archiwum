"""Plot solved active-flap histories and verify the stationary main foil."""
from pathlib import Path
import json
import statistics
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summarize_h010 import get

d=Path(sys.argv[1])
h=get(d/"single_phase.csv")
if not h:
    raise SystemExit("No solved transient steps")
state=json.loads((d/"SOLVE_STATUS.json").read_text())
def series(name):return np.array([float(r[name]) for r in h])
t=series("time_s")
q=series("delta_measured_deg")
ref=series("delta_command_deg")
fig,axes=plt.subplots(3,2,figsize=(10,7),sharex=True,layout="constrained")
ax=axes.flat
ax[0].plot(t,ref,ls="--",color="#383838",label="Command")
ax[0].plot(t,q,color="#3278ac",alpha=.75,label="Measured vertices")
ax[0].legend(frameon=False)
ax[0].set_ylabel("Flap angle [deg]")
for i,k,label in ((1,"CL","CL"),(2,"CD","CD"),(3,"Mh_Nm","Hinge moment [N m/m]"),
                  (4,"pABSmin_Pa","Minimum pABS [kPa]"),(5,"max_CFL","Maximum CFL")):
    ax[i].plot(t,series(k)/(1000 if i==4 else 1))
    ax[i].set_ylabel(label)
ax[4].axhline(12.3392148,color="red",lw=1,ls="--")
ax[5].axhline(25,color="red",lw=1,ls="--")
for a in ax:a.grid(alpha=.25)
for a in axes[-1]:a.set_xlabel("Physical time [s]")
fig.suptitle(f"True 2D SST URANS | U = {state['U_m_s']} m/s | {state['status']}")
fig.savefig(d/"ACTIVE_FLAP_SOLVED_HISTORY.png",dpi=185)
anchor=d/"vertices_0000.csv"
main_shift={}
if anchor.exists():
    a=np.loadtxt(anchor,delimiter=",",skiprows=1)[:,:2]
    a=np.unique(a[a[:,0]<.95],axis=0)
    for f in sorted(d.glob("vertices_step*.csv")):
        b=np.loadtxt(f,delimiter=",",skiprows=1)[:,:2]
        distances=np.linalg.norm(a[:,None,:]-b[None,:,:],axis=-1)
        main_shift[f.name]=float(distances.min(axis=1).max())
metrics=dict(steps=len(h),angle_min=float(q.min()),angle_max=float(q.max()),tracking_error_deg=float(abs(q-ref).max()),
    main_displacement_m=main_shift,max_CFL=float(series("max_CFL").max()),
    min_pABS_kPa=float(series("pABSmin_Pa").min()/1000),min_pbody_kPa=float(series("pbody_min_Pa").min()/1000),
    min_volume_m3=float(series("volume_min").min()),min_face_validity=float(series("face_validity").min()),
    min_quality=float(series("quality").min()),max_mass_error_after_step_5=float(series("mass_relative")[5:].max()) if len(h)>5 else None,
    median_solver_s=statistics.median(series("solver_s")[5:]) if len(h)>5 else None,
    CL_range=series("CL")[[int(series("CL").argmin()),int(series("CL").argmax())]].tolist(),
    CD_range=series("CD")[[int(series("CD").argmin()),int(series("CD").argmax())]].tolist(),
    Mh_range=series("Mh_Nm")[[int(series("Mh_Nm").argmin()),int(series("Mh_Nm").argmax())]].tolist())
(d/"ACTIVE_FLAP_METRICS.json").write_text(json.dumps(metrics,indent=2))
print(json.dumps(metrics,indent=2))

