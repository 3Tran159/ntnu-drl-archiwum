"""Optimize cycle-mean drag at a prescribed cycle-mean vertical load."""
import json
from pathlib import Path

import numpy as np

from compare_mpc import (
    M, TS, P, D, flow_at, forces_grid, lattice, model, plt,
)

HERE = Path(__file__).resolve().parent
TARGET = .60
PHASES = np.arange(model.N) * model.DT
KNOTS = np.arange(M + 1) * TS
FLOW = [flow_at(t) for t in PHASES]
BETA = np.array([state[2] for state in FLOW])
SCALE = np.array([state[3] for state in FLOW])


def evaluate(pitch, flap):
    return np.array([model.forces(p, d, flow) for p, d, flow in zip(pitch, flap, FLOW)])


def fixed_reference():
    lower = max(model.PITCH_MIN, model.ALPHAS[0] - np.degrees(BETA.min()))
    upper = min(model.PITCH_MAX, model.ALPHAS[-1] - np.degrees(BETA.max()))
    candidates = []
    for flap in np.linspace(-model.FLAP_LIMIT, model.FLAP_LIMIT, 121):
        polar = model.delta_polar(flap)
        def lift(pitch):
            a = pitch + np.degrees(BETA)
            cl, cd = (np.interp(a, model.ALPHAS, col) for col in polar.T)
            return np.mean(SCALE * (cl*np.cos(BETA) + cd*np.sin(BETA)))
        if not lift(lower) <= TARGET <= lift(upper):
            continue
        lo, hi = lower, upper
        for _ in range(24):
            mid = (lo+hi)/2
            if lift(mid) < TARGET:
                lo = mid
            else:
                hi = mid
        pitch = np.full(model.N,(lo+hi)/2)
        deflection = np.full(model.N,flap)
        values = evaluate(pitch,deflection)
        candidates.append((values[:,1].mean(),pitch,deflection,values))
    return min(candidates,key=lambda item:item[0])


def optimizer():
    lift,drag,valid = (np.array(x) for x in zip(*(forces_grid(k*TS) for k in range(M))))
    next_idx,_ = lattice()
    p,d = P.ravel(),D.ravel()
    # Bound the incidence along each linear move using both pitch endpoints
    # and the flow-angle extrema within the time interval.
    angles = np.array([[np.degrees(flow_at((k+j/16)*TS)[2]) for j in range(17)] for k in range(M)])
    pmin,pmax = np.minimum(p[:,None],p[next_idx]),np.maximum(p[:,None],p[next_idx])
    invalid = ((pmin[None,:,:] + angles.min(axis=1)[:,None,None] < model.ALPHAS[0]+1e-4)
               | (pmax[None,:,:] + angles.max(axis=1)[:,None,None] > model.ALPHAS[-1]-1e-4))
    invalid |= ~valid[:,:,None]
    rows = np.arange(p.size)

    def schedule(multiplier):
        stage = drag + multiplier*lift
        value = np.zeros_like(p)
        policy = np.empty((M,p.size),dtype=np.int32)
        for _ in range(6):
            for k in range(M-1,-1,-1):
                end = stage[(k+1)%M] + value
                candidates = np.where(invalid[k], np.inf, end[next_idx])
                choices = np.argmin(candidates,axis=1)
                policy[k] = next_idx[rows,choices]
                value = candidates[rows,choices]
            value -= np.min(value)
        state = rows.copy()
        states = [state]
        for move in policy:
            state = move[state]
            states.append(state)
        closed = (state == rows) & np.isfinite(value)
        assert closed.any(), "No closed one-period path on the control grid"
        states = np.array(states)[:,closed]
        total = np.sum(stage[np.arange(M)[:,None],states[:-1]],axis=0)
        path = states[:,np.argmin(total)]
        assert path[0] == path[-1]
        pitch = np.interp(PHASES,KNOTS,p[path])
        flap = np.interp(PHASES,KNOTS,d[path])
        return pitch,flap,evaluate(pitch,flap)
    return schedule


def match_mean(schedule):
    low, high = -.10,.10
    above, below = schedule(low),schedule(high)
    assert above[2][:,0].mean() >= TARGET >= below[2][:,0].mean()
    for _ in range(22):
        mid = (low+high)/2
        data = schedule(mid)
        if data[2][:,0].mean() > TARGET:
            low,above = mid,data
        else:
            high,below = mid,data
    # Interpolate adjacent dual solutions, then re-evaluate the actual angles
    # and their actual loads. Both endpoint schedules have periodic angles.
    lo,hi = 0.,1.
    for _ in range(26):
        w = (lo+hi)/2
        pitch = w*above[0] + (1-w)*below[0]
        flap = w*above[1] + (1-w)*below[1]
        values = evaluate(pitch,flap)
        if values[:,0].mean() < TARGET:
            lo = w
        else:
            hi = w
    return pitch,flap,values


def summarize(pitch,flap,values):
    cl,cd = values.T
    angles = np.column_stack((pitch,flap))
    circular = np.max(abs(np.roll(angles,-1,axis=0)-angles),axis=0) / model.DT
    assert np.all(circular <= model.RATES + 1e-8)
    assert abs(cl.mean()-TARGET) < 1e-6
    return dict(CL_mean=float(cl.mean()),CL_min=float(cl.min()),CL_max=float(cl.max()),
                CD_x_mean=float(cd.mean()),CD_x_min=float(cd.min()),CD_x_max=float(cd.max()),
                negative_drag_fraction=float(np.mean(cd<0)),
                pitch_deg=[float(pitch.min()),float(pitch.max())],
                flap_deg=[float(flap.min()),float(flap.max())],
                peak_rates_deg_s=circular.tolist())


def main():
    _,p_fixed,d_fixed,fixed = fixed_reference()
    pitch,flap,active = match_mean(optimizer())
    baseline=summarize(p_fixed,d_fixed,fixed)
    controlled=summarize(pitch,flap,active)
    result=dict(status="XFOIL_DIAGNOSTIC_ONLY",target_CL_mean=TARGET,
                H_m=model.HEIGHT,wavelength_m=model.WAVELENGTH,U_m_s=model.U,
                encounter_period_s=model.PERIOD,static_reference=baseline,active=controlled,
                delta_CD_x=controlled["CD_x_mean"]-baseline["CD_x_mean"],
                delta_CD_x_pct=100*(controlled["CD_x_mean"]/baseline["CD_x_mean"]-1),
                hinge_and_pitch_work_included=False,method="Periodic preview optimization with actuator limits")
    (HERE/"W04_MEAN_LIFT_060.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    np.savetxt(HERE/"W04_MEAN_LIFT_060.csv",np.column_stack((PHASES,pitch,flap,active,p_fixed,d_fixed,fixed)),
               delimiter=",",comments="",header="t_s,pitch_deg,flap_deg,CL,CD_x,fixed_pitch_deg,fixed_flap_deg,fixed_CL,fixed_CD_x")
    fig,axes=plt.subplots(2,2,sharex=True,figsize=(11,7.4))
    fig.subplots_adjust(left=.09,right=.96,top=.81,bottom=.13,wspace=.30,hspace=.25)
    fig.text(.09,.962,"Minimizing drag at a fixed cycle-mean lift",weight="bold",fontsize=22,va="top")
    fig.text(.09,.902,"W04 head wave · H = 1.50 m · λ = 39.0 m · U = 18 m/s · XFOIL preview model",fontsize=11)
    for ax,curve,base,y in zip(axes.flat,(pitch,flap,active[:,0],active[:,1]),
                               (p_fixed,d_fixed,fixed[:,0],fixed[:,1]),
                               ("Whole-foil angle [deg]","Flap deflection [deg]",
                                "Vertical lift coefficient","Streamwise drag coefficient")):
        ax.plot(PHASES,curve,color="#176d84",lw=2,label="Optimized pitch and flap")
        ax.plot(PHASES,base,color="#677484",lw=1.5,ls="--",label="Best fixed trim at equal mean lift")
        ax.set_ylabel(y)
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(alpha=.22)
        ax.set_xlim(0,model.PERIOD)
    axes[1,0].axhline(TARGET,color="#222c38",lw=.7,ls=":")
    axes[1,1].axhline(0,color="#222c38",lw=.7,ls=":")
    for ax in axes[1]:
        ax.set_xlabel("Time within one encounter cycle [s]")
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="upper left",bbox_to_anchor=(.083,.88),ncol=2,frameon=False)
    fig.text(.09,.036,"Both cases have mean lift coefficient 0.60. No instantaneous lift target or actuator-work term.",fontsize=9)
    fig.savefig(HERE/"W04_MEAN_LIFT_060.png",dpi=170,facecolor="white")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()