import csv
from pathlib import Path
import sys
sys.path.insert(0,r"F:/ntnu/flap_control/exploration_lab/MINI_POC_2D_20261103/mini_vof_20261103/COMEBACK_20261104/WALL_FUNCTIONS_AUDIT/ACTIVE_GAP25_PRISM_20261104/plot_dependencies")
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt

A=Path(r"T:/FLAPS_ARCHIVE/SEALED_GAP_2D_U18_20261104")
O=A/"FLAP_EXTREMA_VOF5_20261105"
cases=(
 (A/"SHARP_SEALED_CYCLE_RESUME_1P064S/single_phase_combined.csv",1.05,"Sharp sealed","#576979","--"),
 (A/"NIGHT_FLAP_20261104/GAP_PLUS_MINUS_2/cycle_full_available.csv",1.0,"2.5 mm gap","#824378","-"),
)

def read(path):
    with path.open(newline="") as f:
        return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]

def time_plot():
    fig,axes=plt.subplots(3,1,sharex=True,figsize=(9.5,7.4),layout="constrained")
    for path,origin,label,color,style in cases:
        rows=read(path)
        if len(rows)!=800:
            raise ValueError("Expected 800 CFD samples for each complete cycle")
        x=[1000*(r["time_s"]-origin) for r in rows]
        for ax,(key,ylabel) in zip(axes,(("delta_measured_deg","Measured deflection [deg]"),
                                        ("CL","Lift coefficient, $C_L$"),("CD","Drag coefficient, $C_D$"))):
            ax.plot(x,[r[key] for r in rows],ls=style,color=color,lw=1.8,label=label)
            for t in (50,150):
                ax.axvline(t,color="#999999",ls=":",lw=.75,zorder=0)
            ax.grid(alpha=.20)
            ax.set_ylabel(ylabel)
    axes[1].legend(frameon=False)
    axes[-1].set_xlim(0,200)
    axes[-1].set_xlabel("Time since start of flap motion [ms]")
    fig.suptitle("Complete ±2° flap cycle | 18 m/s | single-phase URANS")
    fig.savefig(O/"complete_plus_minus_2_time_EN.png",dpi=190)
    plt.close(fig)

def pressure_plot():
    frames=(("SEALED_MINUS2","Sharp sealed",1.100,-2.),("GAP_MINUS2","2.5 mm gap",1.050,-2.),
            ("SEALED_PLUS2","Sharp sealed",1.200,2.),("GAP_PLUS2","2.5 mm gap",1.150,2.))
    fig,axes=plt.subplots(2,2,figsize=(12.8,8.8),layout="constrained")
    for ax,(name,label,time,angle) in zip(axes.flat,frames):
        folder=O/name
        data=read(folder/"pressure_flap.csv")
        row=min(data,key=lambda r:r["Absolute Pressure (Pa)"])
        native=plt.imread(folder/"native_pressure.png")
        height,width=native.shape[:2]
        k=height/.60
        x=width/2+(row["X (m)"]-1.03)*k
        y=height/2-(row["Y (m)"]-.02)*k
        pressure=row["Absolute Pressure (Pa)"]/1000
        ax.imshow(native)
        ax.set_axis_off()
        ax.set_title(f"{label}  |  {angle:+.0f}°  |  t = {time:.3f} s",loc="left",fontsize=12,fontweight="bold")
        ax.annotate(f"Flap-wall minimum: {pressure:.2f} kPa",(x,y),xytext=(max(x+105,610),min(y-135,280)),
                    color="#17222d",fontsize=10,bbox=dict(boxstyle="round,pad=0.32",fc="white",ec="#627281",alpha=.95),
                    arrowprops=dict(arrowstyle="-|>",color="#17222d",lw=1.05))
        print(name,pressure,row["X (m)"],row["Y (m)"])
    fig.suptitle("Absolute pressure at flap extrema | 18 m/s | single-phase URANS")
    fig.savefig(O/"absolute_pressure_plus_minus_2_EN.png",dpi=190,facecolor="white")
    plt.close(fig)

if __name__=="__main__":
    time_plot() if sys.argv[1]=="time" else pressure_plot()

