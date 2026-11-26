from pathlib import Path
import csv
import json
import sys
import numpy as np

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent))
from plot_gap import plt

RUNS=OUT.parents[2]/"runs"
styles=(("SHARP_SEALED","Sharp sealed","#576979","--"),("GAP","2.5 mm gap","#824378","-"))


def read(file):
    if not file.exists():
        return {}
    with file.open(newline="") as stream:
        reader=csv.DictReader(stream)
        rows=[r for r in reader if all(v not in (None,"") for v in r.values())]
    return {k:np.array([float(r[k]) for r in rows]) for k in rows[0]} if rows else {}


def plot():
    status=json.loads((OUT/"RESULT.json").read_text())
    data=[]
    for key,label,color,style in styles:
        folders=sorted(RUNS.glob(f"MATCHED_FIXED_{key}_*"),key=lambda folder: folder.name.rsplit("_",2)[-2:])
        if not folders:
            continue
        folder=folders[-1]
        fixed=read(folder/"fixed_history.csv")
        combined=folder/"single_phase_combined.csv"
        active=read(combined if combined.exists() else folder/"single_phase.csv")
        if fixed or active:
            data.append((label,color,style,fixed,active))
    if not data:
        return

    fig,axs=plt.subplots(3,2,figsize=(11,8),sharex=True,layout="constrained")
    fields=(("CL","CL","Lift coefficient, $C_L$",1,0),("CD","CD","Drag coefficient, $C_D$",1,0),
            (None,"delta_measured_deg","Measured flap deflection [deg]",1,0),
            ("Mh_Nm","Mh_Nm","Hinge moment [N m/m]",1,0),
            ("pflap_Pa","pflap_min_Pa","Flap pressure margin [kPa]",.001,2.3392147668),
            ("CFL","max_CFL","Maximum CFL",1,0))
    for i,(fk,ak,ylabel,scale,offset) in enumerate(fields):
        ax=axs.flat[i]
        for label,color,style,fixed,active in data:
            if fixed:
                t=fixed["physical_time_s"]
                y=fixed[fk]*scale-offset if fk else np.zeros(len(t))
                ax.plot(t,y,color=color,ls=style,label=label,lw=1.6)
            if active:
                t=active["time_s"]
                ax.plot(t,active[ak]*scale-offset,color=color,ls=style,lw=1.65,label=label if not fixed else None)
                ax.axvline(t[0],color=color,ls=":",alpha=.45,lw=.8)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=.22)
    axs.flat[4].axhline(10,ls=":",color="#a9482b",lw=1)
    axs.flat[5].axhline(25,ls=":",color="#a9482b",lw=1)
    axs[0,0].legend(frameon=False)
    for ax in axs[-1]:ax.set_xlabel("Physical time [s]")
    fig.suptitle("Sharp sealed and gapped flap | 18 m/s\nFixed 0° stabilization followed by prescribed motion when gates pass")
    fig.savefig(OUT/"full_histories_EN.png",dpi=190)
    plt.close(fig)

    if not any(active for _,_,_,_,active in data):
        return
    fig,axs=plt.subplots(2,1,figsize=(8.6,6.9),sharex=True,layout="constrained")
    for ax,k in zip(axs,("CL","CD")):
        for label,color,style,_,active in data:
            if not active:
                continue
            angle=active["delta_measured_deg"]; v=active[k]
            step=active["time_s"][1]-active["time_s"][0] if len(angle)>1 else None
            expected=round(.2/step) if step else None
            coverage="" if len(angle)==expected else f" | partial, {len(angle)} steps"
            ax.plot(angle,v,color=color,ls=style,lw=1.65,label=label+coverage)
            ax.scatter(angle[0],v[0],s=24,facecolor="white",edgecolor=color,zorder=4)
            ax.scatter(angle[-1],v[-1],s=24,facecolor=color,zorder=4)
        ax.axvline(0,color="#a6a6a6",lw=.75)
        ax.grid(alpha=.22)
        ax.set_ylabel("Lift coefficient, $C_L$" if k=="CL" else "Drag coefficient, $C_D$")
    axs[0].legend(frameon=False)
    axs[1].set_xlabel("Measured flap deflection [deg] | positive = trailing edge down")
    fig.suptitle("Lift and drag during flap motion | 18 m/s\n"
                 "Open marker: first sample   ·   Filled marker: final sample")
    fig.savefig(OUT/"CL_CD_vs_deflection_EN.png",dpi=190)
    plt.close(fig)


if __name__=="__main__":
    plot()



