"""Assess measured Stokes V harmonics against the native inlet solution."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np

K=2*math.pi/10
U=18.
DEPTH=12.02128173276777
H=.50
EPS=K*H/2
G=9.81

def theoretical_period():
    s=1/math.cosh(2*K*DEPTH)
    c0=math.sqrt(math.tanh(K*DEPTH))
    c2=c0*(2+7*s*s)/(4*(1-s)**2)
    c4=c0*(4+32*s-116*s*s-400*s**3-71*s**4+146*s**5)/(32*(1-s)**5)
    return 10/(U+math.sqrt(G/K)*(c0+c2*EPS**2+c4*EPS**4))

def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def harmonics(t,y,period):
    theta=2*np.pi*t/period
    cols=[np.ones(len(t))]
    for j in range(1,6):
        cols.extend((np.cos(j*theta),np.sin(j*theta)))
    mat=np.column_stack(cols)
    coef=np.linalg.lstsq(mat,y,rcond=None)[0]
    z=coef[1::2]-1j*coef[2::2]
    return z, float(np.sqrt(np.mean((mat@coef-y)**2)))

def review(run):
    h=rows(run/"history.csv")
    g=rows(run/"gauges.csv")
    setup=json.loads((run/"STOKES_READBACK.json").read_text(encoding="utf8"))
    first=json.loads((run/"STOKES_AFTER_FIRST_STEP.json").read_text(encoding="utf8"))
    final_path=run/"STOKES_AFTER_FINAL_STEP.json"
    final=json.loads(final_path.read_text(encoding="utf8")) if final_path.is_file() else {}
    period=final.get("native_period_s") or first.get("native_period_s") or setup.get("native_period_s")
    native_period=period
    if not period or not .40<=period<=.52:
        period=theoretical_period()
    groups={x:[r for r in g if float(r["x_m"])==x] for x in sorted({float(r["x_m"]) for r in g})}
    t=np.array([float(r["time_s"]) for r in h])
    cfg=json.loads((run/"job.json").read_text(encoding="utf8"))
    analysis_start=float(cfg.get("analysis_start_s", t[0]+period))
    retained=t[-1]-analysis_start
    report=dict(status="DIAGNOSTIC",samples=len(h),native_period_s=native_period,estimate_period_s=theoretical_period(),
        sample_span_s=float(t[-1]-t[0]),spatial_cells_per_harmonic=[80/n for n in range(1,6)],
        temporal_steps_per_harmonic=[period/.001/n for n in range(1,6)],
        interface_CFL_max=max(float(r["interface_CFL"]) for r in h),
        pABS_min_Pa=min(float(r["pABSmin_Pa"]) for r in h),
        residual_state=json.loads((run/"SOLVE_STATUS.json").read_text(encoding="utf8"))["status"])
    report["eta_vs_native_rms_m"]=float(np.sqrt(np.mean([(float(r["eta_actual_m"])-float(r["eta_native_theory_m"]))**2 for r in g])))
    if retained<3*period-.003:
        report["reason"]="Short time span, no full-cycle harmonic or propagation gate"
    else:
        reasons=[]
        summaries=[]
        z=[]
        phase=[]
        for x, series in groups.items():
            tt=np.array([float(r["time_s"]) for r in series])
            m=tt>=analysis_start
            t1=tt[m]
            y=np.array([float(r["eta_actual_m"]) for r in series])[m]
            target=np.array([float(r["eta_native_theory_m"]) for r in series])[m]
            c,_=harmonics(t1,y,period)
            c0,_=harmonics(t1,target,period)
            scan=np.linspace(.97,1.03,81)
            best=float(min(scan,key=lambda q:harmonics(t1,y,period*q)[1]))
            angle=float(np.degrees(np.angle(c[0]/c0[0])))
            error=float(np.sqrt(np.mean((y-target)**2)))
            h_rel=(float(np.max(y))-float(np.min(y)))/H-1
            fundamental=float(abs(c[0]/c0[0])-1)
            second=float(abs(c[1]-c0[1]))
            if abs(h_rel)>.10 or abs(fundamental)>.10 or abs(angle)>10 or abs(best-1)>.02 or error>.15*H/2:
                reasons.append(f"Propagation tolerance x={x:g}")
            if second>max(.005,.25*abs(c0[1])):
                reasons.append(f"Second harmonic tolerance x={x:g}")
            per=[]
            for i in range(3):
                mm=(t1>=analysis_start+i*period)&(t1<analysis_start+(i+1)*period)
                per.append(float(abs(harmonics(t1[mm],y[mm],period)[0][0])))
            if max(per)-min(per)>.02*H/2:
                reasons.append(f"Cycle repeatability x={x:g}")
            summaries.append(dict(x_m=x,amps_m=list(abs(c)),target_amps_m=list(abs(c0)),phase_error_deg=angle,
                                  fit_period_s=period*best,eta_rms_m=error,relative_height_error=h_rel))
            z.append(c[0])
            phase.append(x)
        omega=2*math.pi/period
        kr=((math.sqrt(G)+math.sqrt(G+4*U*omega))/(2*U))**2
        x=np.array(phase)
        # Diagnostic: Doppler-shifted opposite intrinsic branch is also advected downstream.
        mat=np.column_stack([np.exp(-1j*K*x),np.exp(-1j*kr*x)])
        a=np.linalg.lstsq(mat,np.array(z),rcond=None)[0]
        reflected=float(abs(a[1]/a[0]))
        if reflected>.05 or np.sqrt(np.mean(abs(mat@a-z)**2))>.05*H/2:
            reasons.append("Opposite branch or fit residual")
        if report["residual_state"]!="NUMERICAL_END_PASS":
            reasons.append("Native final residual window or physical safety unresolved; review inner reduction, mass and dt sensitivity")
        if report["interface_CFL_max"]>.5 or report["pABS_min_Pa"]<=12339.214766776897:
            reasons.append("Physical safety")
        if any(float(r["mass_relative"])>1e-4 or float(r["volume_min"])<=0 for r in h[5:]):
            reasons.append("Mass/mesh safety")
        report.update(status="PASS_PROPAGATION" if not reasons else "HOLD", reasons=reasons,
                      harmonics=summaries,opposite_branch_ratio=reflected)
        if (run/"gauges_absorption.csv").exists():
            absorb=rows(run/"gauges_absorption.csv")
            report["damping_zone_h1_m"]={}
            for location in (20.5,24,27):
                a=[r for r in absorb if float(r["x_m"])==location and float(r["time_s"])>=analysis_start]
                if a:
                    ta=np.array([float(r["time_s"]) for r in a])
                    ya=np.array([float(r["eta_actual_m"]) for r in a])
                    report["damping_zone_h1_m"][str(location)]=float(abs(harmonics(ta,ya,period)[0][0]))
    (run/"STOKES_REVIEW.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    print(json.dumps(review(parser.parse_args().run),indent=2))


