from pathlib import Path
import json
import sys

D = Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent))
from plot_gap import read_history, plt

status=json.loads((D/"RESULT.json").read_text())
folder=Path(status["BASELINE"]["checkpoint"]).parent
h=read_history(folder/"steady_history.csv")
fig,ax=plt.subplots(figsize=(8.2,4.8),layout="constrained")
for key,label,color in (("pbody","Foil wall minimum (leading edge)","#a9482b"),
                        ("pABSmin","Domain cell minimum","#576979"),
                        ("pflap_Pa","Flap wall minimum","#127a92"),
                        ("pgap_Pa","Hinge pocket minimum","#40826d")):
    ax.plot(420+h["iteration"],h[key]/1000,label=label,color=color)
ax.axhline(2.3392147668,color="#a9482b",ls="--",lw=1,label="Global vapor-pressure floor")
ax.axhline(12.3392147668,color="#127a92",ls=":",lw=1,label="Flap and gap stop limit")
ax.scatter(491,h["pbody"][-1]/1000,c="#a9482b",zorder=5)
ax.set(xlabel="Steady solver iteration",ylabel="Minimum absolute pressure [kPa]",
       title="Gapped flap at 0° | Checkpoint continuation at 18 m/s")
ax.legend(frameon=False,ncol=2,loc="center")
ax.grid(alpha=.2)
fig.savefig(D/"LOCAL_PRESSURE_GATE_EN.png",dpi=190)

