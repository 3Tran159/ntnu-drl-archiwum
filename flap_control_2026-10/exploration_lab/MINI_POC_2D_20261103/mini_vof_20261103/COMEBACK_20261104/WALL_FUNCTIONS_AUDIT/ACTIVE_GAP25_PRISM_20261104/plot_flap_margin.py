from pathlib import Path
import json
from plot_aft_cycles import OUT, read_history, plt

d=OUT/"SEALED_OUTER_MESH_GAPPED"
r=json.loads((d/"RESULT_DT0333MS.json").read_text())["DT0333MS"]
h=read_history(Path(r["checkpoint"]).parent/"single_phase.csv")
a=h["delta_measured_deg"]
margin=h["flap_vapor_margin_Pa"]/1000
fig,ax=plt.subplots(figsize=(8.3,4.8),layout="constrained")
ax.plot(a,margin,c="#236e8a",lw=1.7,label="Flap wall minimum above vapor pressure")
ax.scatter(a[0],margin[0],s=32,facecolor="white",edgecolor="#236e8a",zorder=4,label="First sample")
ax.scatter(a[-1],margin[-1],s=44,c="#9b4252",zorder=4,label="Pressure stop")
ax.axhline(10,c="#9b4252",ls="--",lw=1,label="Required 10 kPa margin")
ax.annotate(f'{a[-1]:+.3f}°, {margin[-1]:.2f} kPa',
            (a[-1],margin[-1]),xytext=(-90,18),textcoords="offset points",color="#9b4252")
ax.set(xlabel="Measured flap deflection [deg] | positive = trailing edge down",
       ylabel="Minimum flap pressure above vapor pressure [kPa]",
       title="Gapped flap in the sealed outer mesh | 18 m/s, time step 0.333 ms")
ax.grid(alpha=.22)
ax.legend(frameon=False)
fig.savefig(d/"FLAP_PRESSURE_MARGIN_VS_DEFLECTION_EN.png",dpi=190)

