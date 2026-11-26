import csv,json,sys,os,statistics
from pathlib import Path
import numpy as np

base=Path(__file__).resolve().parent
cb=base.parent
os.environ["MPLCONFIGDIR"]=str(cb/"mpl_cache")
sys.path.insert(0,str(cb.parents[3]/"hydro_validation_2606_20261102"/"tools"/"deps"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def rows(p):
    with p.open(newline="",encoding="utf8") as f:return list(csv.DictReader(f))

def wave():
    a=next((cb/"runs").glob("SPRINT_A_RAMP40_CFL_SAFE*"))
    b=next((cb/"runs").glob("A_STOKES_CONTINUITY_DIAGNOSTIC*"))
    h=rows(a/"history.csv")+rows(b/"history.csv")
    g=rows(a/"gauges.csv")+rows(b/"gauges.csv")
    q=rows(a/"residual_per_step.csv")+rows(b/"residual_per_step.csv")
    t=np.array([float(v["time_s"]) for v in h])
    fig,ax=plt.subplots(2,2,figsize=(10,7),layout="constrained")
    for x in (-6,.952,12):
        s=[v for v in g if float(v["x_m"])==x]
        ax[0,0].plot([float(v["time_s"]) for v in s],[float(v["eta_actual_m"])*1000 for v in s],label=f"x={x:g} m")
    ax[0,0].set(ylabel="CFD elevation [mm]")
    ax[0,0].legend(frameon=False)
    for name in ("Continuity","X-momentum","Y-momentum","Sdr"):
        v=[r for r in q if r["monitor"]==name]
        ax[0,1].semilogy([float(r["time_s"]) for r in v],[float(r["last"]) for r in v],label=name)
    ax[0,1].axhline(.01,color=".4",ls=":")
    ax[0,1].set(ylabel="Normalized final inner residual")
    ax[0,1].legend(frameon=False,fontsize=8)
    ax[1,0].semilogy(t,[max(float(v["mass_relative"]),1e-18) for v in h])
    ax[1,0].axhline(1e-4,color=".4",ls=":")
    ax[1,0].set(ylabel="Relative mass imbalance")
    ax[1,1].plot(t,[float(v["nut_ratio_max"]) for v in h])
    ax[1,1].set(ylabel="Maximum turbulent viscosity ratio")
    for a0 in ax.flat:
        a0.set_xlabel("Physical time [s]")
        a0.axvline(.04,color=".5",ls="--",lw=.8)
        a0.grid(alpha=.18)
    fig.suptitle("Stokes V | actual ramp CFD | HOLD residual window")
    fig.savefig(base/"STOKES_RAMP_ACTUAL_HISTORY.png",dpi=180)
    plt.close(fig)
    result=dict(steps=len(h),last_time_s=float(t[-1]),pABSmin_Pa=min(float(v["pABSmin_Pa"]) for v in h),
        max_interface_CFL=max(float(v["interface_CFL"]) for v in h), max_mut_mu=max(float(v["nut_ratio_max"]) for v in h),
        max_mass=max(float(v["mass_relative"]) for v in h[5:]),
        resumed_wall_step_s=statistics.mean(float(v["step_wall_s"]) for v in rows(b/"step_wall.csv")[5:]))
    (base/"STOKES_RAMP_MEASUREMENTS.json").write_text(json.dumps(result,indent=2),encoding="utf8")
    print(result)

def moving(run):
    h=rows(run/"single_phase.csv")
    t=[float(r["time_s"]) for r in h]
    if len(t)<2:raise ValueError("Too few CFD samples")
    fig,ax=plt.subplots(3,2,figsize=(10,8),layout="constrained")
    for axis,name,unit in zip(ax.flat,("delta_measured_deg","CL","CD","Mh_Nm","pABSmin_Pa","max_CFL"),
                              ("Flap angle [deg]","CL","CD","Mh [Nm for 1 m span]","Minimum pABS [Pa]","Max. CFL")):
        axis.plot(t,[float(r[name]) for r in h],color="#176989")
        axis.set(xlabel="Physical time [s]",ylabel=unit)
        axis.grid(alpha=.2)
    ax[0,0].plot(t,[float(r["delta_command_deg"]) for r in h],color=".5",ls="--",lw=.9)
    fig.suptitle("Single-phase sealed foil | STAR CFD, seeded transient")
    fig.savefig(run/"SEEDED_URANS_ACTUAL_HISTORY.png",dpi=175)
    plt.close(fig)

if __name__=="__main__":
    if len(sys.argv)==1:wave()
    else:moving(Path(sys.argv[1]))

