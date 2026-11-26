from pathlib import Path
import json

from plot_gap import OUT, plt, read_history

status = json.loads((OUT/"RESULT.json").read_text())
folder = Path(status["BASELINE"]["checkpoint"]).parent
h = read_history(folder/"steady_history.csv")
n = h["iteration"]
domain = "#127a92"
wall = "#c56732"
fig, axes = plt.subplots(3, 1, figsize=(8.8,7.8), sharex=True, layout="constrained")
axes[0].plot(n, h["U_m_s"], color="#576979")
axes[0].set_ylabel("Inlet speed [m/s]")
axes[1].plot(n, h["pABSmin"]/1000,label="Domain minimum",color=domain)
axes[1].plot(n, h["pbody"]/1000,label="Wall minimum",color=wall)
axes[1].axhline(12.3392147668,color="#8a3e32",ls="--",lw=1,label="Pressure stop limit")
axes[1].scatter(n[-1],h["pbody"][-1]/1000,color=wall,zorder=5)
axes[1].annotate(f'{h["pbody"][-1]/1000:.2f} kPa',
                 (n[-1],h["pbody"][-1]/1000),xytext=(-66,12),textcoords="offset points",color=wall)
axes[1].set_ylabel("Absolute pressure [kPa]")
axes[1].legend(frameon=False,ncol=2)
axes[2].plot(n,h["pmin_x_m"],label="Domain minimum",color=domain)
axes[2].plot(n,h["pwall_x_m"],label="Wall minimum",color=wall)
axes[2].axhline(.952,color="#818181",ls=":",label="Hinge axis")
axes[2].set(xlabel="Steady solver iteration",ylabel="Minimum-pressure x [m]")
axes[2].legend(frameon=False,ncol=3,loc="upper center")
for ax in axes:
    ax.grid(alpha=.2)
fig.suptitle("Gapped flap at 0° | Pressure during steady initialization\n"
             "Exploratory diagnostic | transient motion has not started",fontweight="bold")
fig.savefig(OUT/"GAPPED_FLAP_STARTUP_PRESSURE_EN.png",dpi=190)

