"""Compare saved TD3 policies with a preview-based lattice MPC on the W04 wave."""
import csv
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import train_energy_td3 as model

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[2] / "plot_deps_312"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

M = 76
HORIZON = 16
TS = model.PERIOD / M
GRID_PITCH = np.linspace(model.PITCH_MIN, model.PITCH_MAX, 26)
GRID_FLAP = np.linspace(-model.FLAP_LIMIT, model.FLAP_LIMIT, 41)
P, D = np.meshgrid(GRID_PITCH, GRID_FLAP, indexing="ij")
SHAPE = P.shape
CL_TARGET = model.TARGET
COLOR = {"pitch_only": "#20738c", "flap_only": "#b26c2c", "combined": "#7c438a", "mpc": "#20916d", "mpc_lift": "#20374d"}
NAME = {"pitch_only": "TD3 · pitch", "flap_only": "TD3 · flap", "combined": "TD3 · pitch + flap",
        "mpc": "MPC · drag + lift", "mpc_lift": "MPC · lift priority"}


def flow_at(t):
    return model.flow(t * 2 * math.pi / model.PERIOD, 1.)


def forces_grid(t):
    _, _, beta, scale = flow_at(t)
    alpha = P.ravel() + math.degrees(beta)
    polys = np.array([model.delta_polar(x) for x in GRID_FLAP])
    a = model.ALPHAS
    valid = (alpha >= a[0]) & (alpha <= a[-1])
    lift = np.zeros(P.size)
    drag = np.zeros(P.size)
    for j, row in enumerate(polys):
        idx = np.arange(j, P.size, D.shape[1])
        cl = np.interp(alpha[idx], a, row[:,0])
        cd = np.interp(alpha[idx], a, row[:,1])
        lift[idx] = scale * (cl * math.cos(beta) + cd * math.sin(beta))
        drag[idx] = scale * (cd * math.cos(beta) - cl * math.sin(beta))
    return lift, drag, valid


def lattice():
    i, j = np.indices(SHAPE).reshape(2, -1)
    pitch_moves = np.array([-16,-12,-8,-4,-2,-1,0,1,2,4,8,12,16])
    flap_moves = np.arange(-3, 4)
    moves = np.array(np.meshgrid(pitch_moves, flap_moves)).reshape(2, -1).T
    assert np.max(abs(pitch_moves))*np.diff(GRID_PITCH).max() <= model.RATES[0]*TS
    assert np.max(abs(flap_moves))*np.diff(GRID_FLAP).max() <= model.RATES[1]*TS
    ni = np.clip(i[:,None] + moves[:,0], 0, SHAPE[0]-1)
    nj = np.clip(j[:,None] + moves[:,1], 0, SHAPE[1]-1)
    effort = .005 * (((GRID_PITCH[ni]-P.ravel()[:,None])/(TS*model.RATES[0]))**2
                     + ((GRID_FLAP[nj]-D.ravel()[:,None])/(TS*model.RATES[1]))**2)
    return (ni*SHAPE[1] + nj).astype(np.int32), effort.astype(np.float32)


def run_mpc(fixed_angles, reference_cd, lift_priority=False):
    start = perf_counter()
    lift, drag, valid = (np.array(x) for x in zip(*(forces_grid(k*TS) for k in range(M))))
    next_idx, effort = lattice()
    phase_indices = np.arange(M)[:,None,None]
    p0, d0 = fixed_angles
    state0 = int(np.argmin((P.ravel()-p0)**2+(D.ravel()-d0)**2))
    # Check each transition at both ends against the most restrictive incident angle
    # in that interval, so intermediate evaluation never extrapolates the polar.
    bounds = np.array([[math.degrees(flow_at((k+j/4)*TS)[2]) for j in range(5)] for k in range(M)])
    p = P.ravel()
    low = np.minimum(p[:,None],p[next_idx])
    high = np.maximum(p[:,None],p[next_idx])
    invalid_path = ((low[None,:,:]+bounds.min(axis=1)[:,None,None] < model.ALPHAS[0])
                    | (high[None,:,:]+bounds.max(axis=1)[:,None,None] > model.ALPHAS[-1]))
    transit = effort[None,:,:] + invalid_path.astype(np.float32)*1e5

    def solve(multiplier):
        load_error = (lift-CL_TARGET)/model.LIFT_BAND
        base = (drag-reference_cd-model.SLOPE*(lift-CL_TARGET))/.001
        # Same soft ±10% band as TD3 and a dual weight for the cycle mean.
        tracking = 24*np.maximum(abs(load_error)-.1,0)**2 if lift_priority else 2*np.maximum(abs(load_error)-1,0)**2
        stage = base + tracking + multiplier*load_error
        stage = (stage + (~valid)*1e5).astype(np.float32)
        future = np.zeros_like(stage)
        for _ in range(HORIZON):
            end_cost = np.roll(future+stage,-1,axis=0)
            candidate = end_cost[phase_indices,next_idx[None,:,:]] + transit
            future = candidate.min(axis=2)
        policy = candidate.argmin(axis=2)
        state = state0
        states = []
        for step in range(5*M+1):
            states.append(state)
            k = step % M
            state = int(next_idx[state,policy[k,state]])
        times = np.arange(model.N)*model.DT
        knots = np.arange(M+1)*TS
        states = np.array(states[-M-1:])
        pitch = np.interp(times,knots,p[states])
        flap = np.interp(times,knots,D.ravel()[states])
        values = np.array([(*model.forces(a,d,flow_at(t)),flow_at(t)[1])
                           for t,a,d in zip(times,pitch,flap)])
        return np.column_stack((times,pitch,flap,values))

    lo,hi=(-20.,20.) if lift_priority else (-4.,4.)
    candidates=[]
    for _ in range(12):
        weight=(lo+hi)/2
        data=solve(weight)
        error=data[:,3].mean()-CL_TARGET
        candidates.append((abs(error),weight,data))
        if error>0:
            lo=weight
        else:
            hi=weight
    _,weight,data=min(candidates,key=lambda row:row[0])
    cl,cd=data[:,3:5].T
    metrics=dict(
        CL_mean=float(cl.mean()),CL_mean_error_pct=float(100*(cl.mean()/CL_TARGET-1)),
        CD_x_mean=float(cd.mean()),delta_CD_vs_same_wave_fixed_pct=float(100*(cd.mean()/reference_cd-1)),
        CL_min=float(cl.min()),CL_max=float(cl.max()),
        CL_in_band_1_pct=float(100*np.mean(abs(cl/CL_TARGET-1)<=.01)),
        CL_in_band_10_pct=float(100*np.mean(abs(cl/CL_TARGET-1)<=.10)),
        mean_lift_comparable=bool(abs(cl.mean()/CL_TARGET-1)<=.001),
        within_band_definition="sample fraction",planning_horizon_s=HORIZON*TS,
        control_update_s=TS,dual_weight=weight,analysis_wall_s=perf_counter()-start)
    tag = "MPC_LIFT_H150" if lift_priority else "MPC_H150"
    np.savetxt(HERE/f"{tag}.csv",data,delimiter=",",comments="",
               header="t_s,pitch_deg,flap_deg,CL_vertical,CD_x,Uz_m_s")
    (HERE/f"{tag}.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    return data,metrics


def plot_control(report,fixed_angles,mpc):
    times = np.arange(model.N)*model.DT
    fixed = np.array([model.forces(*fixed_angles,flow_at(t)) for t in times])
    fig, ax = plt.subplots(3,2,figsize=(12,8.5),sharex=True)
    fig.subplots_adjust(left=.085,right=.97,bottom=.11,top=.83,hspace=.28,wspace=.26)
    fig.text(.085,.963,"Hydrofoil control in the W04 head wave",weight="bold",fontsize=24,va="top")
    fig.text(.085,.907,"H = 1.50 m  ·  λ = 39.0 m  ·  U = 18 m/s  ·  quasi-steady XFOIL pilot",fontsize=12)
    eta=-.75*np.cos(times*2*np.pi/model.PERIOD)
    ax[0,0].plot(times,eta,color="#46596a",lw=1.8)
    ax[0,0].set_ylabel("Incident elevation η [m]")
    fig.delaxes(ax[0,1])
    plot_axes=[ax[1,0],ax[1,1],ax[2,0],ax[2,1]]
    for index,axis in enumerate(plot_axes):
        axis.plot(times,np.full(times.shape,fixed_angles[index]) if index<2 else fixed[:,index-2],
                  color="#5f6974",lw=1.45,ls="--",label="Fixed · equal mean lift")
    for mode in model.MODES:
        history=np.loadtxt(HERE/f"{mode}_H150.csv",delimiter=",",skiprows=1)
        data=history[history[:,0]==0][-model.N:]
        phi0=model.TEST_PHASES[0]+2*np.pi*data[0,1]/model.PERIOD
        t=(np.mod(phi0+2*np.pi*np.arange(len(data))/model.N,2*np.pi)/(2*np.pi))*model.PERIOD
        order=np.argsort(t)
        for index,axis in enumerate(plot_axes):
            axis.plot(t[order],data[order,[4,5,2,3][index]],color=COLOR[mode],lw=1.5,label=NAME[mode])
    for mode, trajectory in mpc.items():
        for index,axis in enumerate(plot_axes):
            axis.plot(trajectory[:,0],trajectory[:,index+1],color=COLOR[mode],lw=1.6,label=NAME[mode])
    ax[2,0].axhline(CL_TARGET,color="#141d25",lw=.7,ls=":")
    ax[2,0].axhspan(.99*CL_TARGET,1.01*CL_TARGET,color="#cdd7e0",alpha=.55,zorder=0)
    ax[2,1].axhline(0,color="#141d25",lw=.7,ls=":")
    for axis,label in zip(plot_axes,["Whole-foil angle α [deg]","Flap deflection δ [deg]",
                                    "Vertical lift coefficient","Streamwise drag coefficient"]):
        axis.set_ylabel(label)
    for axis in [ax[0,0],*plot_axes]:
        axis.grid(alpha=.17)
        axis.set_xlim(0,model.PERIOD)
        axis.spines[["top","right"]].set_visible(False)
    for axis in ax[2,:]:
        axis.set_xlabel("Time within one encounter cycle [s]")
    handles,labels=ax[1,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper left",bbox_to_anchor=(.54,.84),ncol=2,
               frameon=False,fontsize=9.5)
    fig.text(.085,.032,"Shaded lift band is ±1% of the target. Negative instantaneous streamwise drag indicates forward force.",fontsize=9)
    fig.savefig(HERE/"W04_TD3_MPC_CONTROL.png",dpi=170,facecolor="white")


def plot_wave_map():
    base=model.BASE/"ANGLES_PM5/XFOIL_CL_CD_ANGLES_PM5.csv"
    raw={}
    with base.open(newline="") as source:
        for row in csv.DictReader(source):
            if row["status"]=="CONVERGED":
                raw[(float(row["flap_deflection_deg"]),float(row["foil_angle_deg"]))]=[float(row["CL"]),float(row["CD"])]
    angle=np.linspace(-5,5,201)
    flap=np.arange(-5,5.1,.5)
    polar_angles=np.arange(-5,5.1,.5)
    tide=np.array([flow_at(t) for t in np.arange(360)*model.PERIOD/360])
    beta=tide[:,2]
    scale=tide[:,3]
    actual=angle[:,None]+np.degrees(beta)
    cl,cd=(np.full((len(flap),len(angle)),np.nan) for _ in range(2))
    for i,d in enumerate(flap):
        polar=np.array([raw.get((d,a),[np.nan,np.nan]) for a in polar_angles])
        local_lift,local_drag=(np.interp(actual,polar_angles,p,left=np.nan,right=np.nan) for p in polar.T)
        cl[i]=np.mean(scale*(local_lift*np.cos(beta)+local_drag*np.sin(beta)),axis=1)
        cd[i]=np.mean(scale*(local_drag*np.cos(beta)-local_lift*np.sin(beta)),axis=1)
    fig, axes=plt.subplots(1,2,figsize=(11,5))
    fig.subplots_adjust(left=.09,right=.94,bottom=.19,top=.74,wspace=.32)
    fig.text(.09,.945,"Fixed settings in the W04 head wave",weight="bold",fontsize=22,va="top")
    fig.text(.09,.84,"H = 1.50 m  ·  λ = 39.0 m  ·  XFOIL and linear orbital flow at 2 m submergence",fontsize=11)
    for ax,data,title,cmap in zip(axes,[cl,cd],["A   Cycle-mean vertical lift","B   Cycle-mean streamwise drag"],["viridis","cividis"]):
        mesh=ax.pcolormesh(angle,flap,data,cmap=cmap,shading="nearest")
        contour=ax.contour(angle,flap,cl,levels=[CL_TARGET],colors=["#fb784d"],linewidths=1.4)
        ax.clabel(contour,fmt={CL_TARGET:"Target 0.646"},fontsize=9)
        ax.set(xlim=(-5,5),ylim=(-5.25,5.25),xlabel="Whole-foil angle [deg]",
               ylabel="Flap deflection [deg]")
        ax.set_title(title,loc="left",fontsize=12,weight="bold")
        ax.set_facecolor("#e8ebee")
        fig.colorbar(mesh,ax=ax,pad=.026)
    fig.text(.09,.035,"Gray indicates that the local angle leaves the converged XFOIL polar during part of the cycle.",fontsize=9)
    fig.savefig(HERE/"W04_FIXED_WAVE_HEATMAP.png",dpi=170,facecolor="white")


if __name__=="__main__":
    report=json.loads((HERE/"TD3_ENERGY_RESULTS.json").read_text(encoding="utf-8"))
    assert set(report["mode_results"])==set(model.MODES), "Wait for the complete TD3 run"
    fixed_angles=tuple(report[f"common_fixed_{a}_deg"] for a in ("pitch","flap"))
    reference=report["mode_results"]["combined"]["cases"]["1.5"]["fixed"]["CD_x_mean"]
    plot_wave_map()
    data,metrics=run_mpc(fixed_angles,reference)
    tracking,tracking_metrics=run_mpc(fixed_angles,reference,lift_priority=True)
    plot_control(report,fixed_angles,{"mpc":data,"mpc_lift":tracking})
    print(json.dumps(tracking_metrics,indent=2))
    print(json.dumps(metrics,indent=2))