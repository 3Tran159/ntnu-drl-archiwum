"""Publish an explicitly labelled trajectory from STAR history and gauge exports."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OMEGA = 2*math.pi*(18/10 + math.sqrt(9.81/(20*math.pi)))
K = 2*math.pi/10
Q_S = 3855.6
BUOYANCY_0 = 22.717957840926616

def csv_rows(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def num(x):
    try:
        f=float(x)
        return f if math.isfinite(f) else None
    except (TypeError,ValueError):
        return None

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def encounter_period(run):
    for name in ("STOKES_AFTER_FINAL_STEP.json","STOKES_AFTER_FIRST_STEP.json","STOKES_READBACK.json"):
        file=run/name
        if file.is_file():
            readback=json.loads(file.read_text(encoding="utf8"))
            value=num(readback.get("native_period_s"))
            if value is not None and .40<value<.52:
                return value
    if (run/"STOKES_READBACK.json").exists():
        raise ValueError("No valid native Stokes period")
    return 2*math.pi/OMEGA

def export(run, out, status, mesh_id):
    period=encounter_period(run)
    omega=2*math.pi/period
    if status=="ACCEPTED":
        review=json.loads((run/"DATASET_ACCEPTANCE.json").read_text(encoding="utf8"))
        if (review.get("status")!="ACCEPTED" or review.get("run_id")!=run.name or
            any(review.get("sha256",{}).get(f)!=digest(run/f) for f in ("history.csv","gauges.csv","FINAL.sim"))):
            raise ValueError("Dataset acceptance file missing or inconsistent with source files")
        start=float(review["analysis_start_s"])
        end=float(review["analysis_end_s"])
        phase_correction=float(review["local_phase_offset_rad"])
        if end-start < 3*period - .003:
            raise ValueError("Fewer than three retained periods")
    else:
        start,end,phase_correction=-math.inf,math.inf,None
    raw=csv_rows(run/"history.csv")
    gauges={}
    for row in csv_rows(run/"gauges.csv"):
        gauges.setdefault(float(row["time_s"]),{})[float(row["x_m"])]=float(row["eta_actual_m"])
    if not raw:
        raise ValueError("No CFD samples")
    cfg=json.loads((run/"job.json").read_text(encoding="utf-8-sig"))
    foil=bool(cfg.get("foil"))
    wave_present=max(float(cfg.get("amplitude",0)),float(cfg.get("old_amplitude",0)))>0
    xs=sorted({x for g in gauges.values() for x in g})
    rows=[]
    for h in raw:
        t=float(h["time_s"])
        if t not in gauges or set(gauges[t])!=set(xs) or not start<=t<=end:
            continue
        fz=num(h["Fz"])
        p=K*.952-omega*t
        row=dict(run_id=run.name,mesh_id=mesh_id,fidelity_level="quasi2d_one_layer_20mm",
                 physical_time_s=t,wave_phase_nominal_rad=p if wave_present else None,
                 wave_phase_local_rad=p+phase_correction if phase_correction is not None else None,
                 Ux_probe_m_s=num(h["Ux"]),Uz_probe_m_s=num(h["Uy"]),
                 delta_deg=num(h.get("delta_measured_deg")) if cfg.get("moving") else 0 if foil else None,
                 delta_dot_rad_s=num(h.get("delta_dot_rad_s")) if cfg.get("moving") else 0 if foil else None,
                 CL_buoyancy_corrected=num(h["CL"]),CD=num(h["CD"]),Fx_N=num(h["Fx"]),Fz_total_N=fz,
                 Fz_buoyancy_corrected_N=fz-BUOYANCY_0 if fz is not None else None,
                 Mh_fluid_Nm=num(h["Mh"]),hinge_power_fluid_W=num(h.get("hinge_power_fluid_W")),
                 pABS_min_Pa=num(h["pABSmin_Pa"]),pABS_foil_min_Pa=num(h.get("pbody")),
                 pABS_flap_min_Pa=num(h.get("pflap")),interface_CFL=num(h["interface_CFL"]),
                 max_CFL=num(h["max_CFL"]),mass_relative=num(h["mass_relative"]),
                 mesh_volume_min_m3=num(h["volume_min"]),solver_s_per_step=num(h["solver_s"]),
                 numerical_status=status)
        row.update({f"eta_x_{x:g}m":gauges[t][x] for x in xs})
        rows.append(row)
    if not rows:
        raise ValueError("No synchronized CFD samples")
    if status=="ACCEPTED":
        required=("CL_buoyancy_corrected","CD","Mh_fluid_Nm","delta_deg","delta_dot_rad_s","pABS_min_Pa","interface_CFL")
        if not foil or any(row[k] is None for row in rows for k in required):
            raise ValueError("Accepted foil trajectory has missing mandatory measurements")
    out.mkdir(parents=True,exist_ok=True)
    with (out/"trajectory.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    metadata=dict(status=status,train_eligible=status=="ACCEPTED",run_id=run.name,samples=len(rows),
        time_range_s=[rows[0]["physical_time_s"],rows[-1]["physical_time_s"]],mesh_id=mesh_id,
        geometry="modified NACA66-012, sealed demonstration, gap=0" if foil else "empty wave tank",
        frame=dict(streamwise="+X STAR; U=18 m/s; fixed foil frame",vertical="+Y STAR = +Z dataset",
                   span="+Z STAR; hinge axis -Z STAR; positive delta trailing edge down",
                   hinge_star_m=[.952,.02128173276777,.01], chord_m=1.19,span_m=.02),
        encounter_period_s=period,
        wave_type="FifthOrderVofWave" if (run/"STOKES_READBACK.json").exists() else "FirstOrderVofWave",
        phase="eta fundamental = A cos(k*x - omega_e*t + fitted_offset). Nominal phase stored separately.",
        velocity_probe_star_m=[-1.19 if foil else .952,.02128173276777,.01],
        normalization=dict(rho_water_kg_m3=1000,qS_N=Q_S,CD="Fx/qS",
            CL="(Fz_total - fixed zero-angle calm buoyancy reference)/qS",calm_reference_buoyancy_N=BUOYANCY_0,
            note="The reference correction does not remove wave-induced pressure or angle-dependent buoyancy."),
        signed_power="Mh is fluid moment about the positive-deflection axis. Mh*delta_dot is signed fluid-to-flap power, not electrical draw.",
        derivative="Backward difference of measured tip angle for active smoke; units rad/s.",
        train_split="Split only by whole trajectory and wave condition. DIAGNOSTIC and FAILED rows are excluded.",
        source_sha256={f:digest(run/f) for f in ("history.csv","gauges.csv","job.json")},
        run_configuration=cfg)
    (out/"METADATA.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding="utf8")
    return rows

def diagnostic(run,out,rows):
    import os,sys
    os.environ["MPLCONFIGDIR"]=str(HERE/"mpl_cache")
    sys.path.insert(0,str(HERE.parents[3]/"hydro_validation_2606_20261102"/"tools"/"deps"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    raw=csv_rows(run/"history.csv")
    residual=csv_rows(run/"residual_per_step.csv")
    t=np.array([r["physical_time_s"] for r in rows])
    x=np.array([-6,-3,.952,4,8,12,16])
    y=np.array([[r[f"eta_x_{xi:g}m"] for xi in x] for r in rows])
    A=np.column_stack([np.ones(len(x)),np.cos(K*x),np.sin(K*x)])
    c=np.linalg.lstsq(A,y.T,rcond=None)[0]
    fitted_amp=np.hypot(c[1],c[2])
    fitted_phi=np.angle(c[1]+1j*c[2])
    relative_phase=np.angle(np.exp(1j*(fitted_phi-OMEGA*t)))
    nominal=.05*np.cos(K*x[None,:]-OMEGA*t[:,None])
    v=np.array([[float(r["Ux"])-float(r["Ux_theory"]),float(r["Uy"])-float(r["Uy_theory"])] for r in raw])
    rr=[r for r in residual if r["monitor"]=="Continuity"]
    warm=np.array([r["solver_s_per_step"] for r in rows][5:])
    stats=dict(status="DIAGNOSTIC",samples=len(t),duration_s=float(t[-1]-t[0]),
        covered_period_fraction=float((t[-1]-t[0])*OMEGA/(2*math.pi)),
        eta_rmse_vs_airy_m=float(np.sqrt(np.mean((y-nominal)**2))),
        spatial_snapshot_amplitude_m=[float(fitted_amp.min()),float(fitted_amp.max())],
        spatial_snapshot_abs_phase_error_deg_max=float(np.max(abs(np.degrees(relative_phase)))),
        orbital_rmse_m_s=list(np.sqrt(np.mean(v*v,axis=0))),
        continuity_last_range=[min(float(r["last"]) for r in rr),max(float(r["last"]) for r in rr)],
        continuity_last_over_peak_inner_max=max(float(r["last"])/float(r["max_inner"]) for r in rr),
        pABS_min_Pa=min(r["pABS_min_Pa"] for r in rows),
        interface_CFL_max=max(r["interface_CFL"] for r in rows),
        mass_relative_max_after_5=max(r["mass_relative"] for r in rows[5:]),
        solver_s_per_step_mean=float(warm.mean()),solver_s_per_step_median=float(np.median(warm)),
        solver_s_per_step_max=float(warm.max()),period_s=2*math.pi/OMEGA,
        estimates_minutes_excluding_start_save_spinup={str(n):math.ceil(n*2*math.pi/OMEGA/.001)*float(warm.mean())/60 for n in (1,3,5)},
        cannot_assess=["encounter period from CFD","reflection","cycle repeatability","foil forces","active flap"])
    (out/"MEASURED_WAVE.json").write_text(json.dumps(stats,indent=2),encoding="utf8")
    fig,axes=plt.subplots(2,2,figsize=(10,6),layout="constrained")
    fig.suptitle("Mini-VOF empty tank · native CFD · diagnostic segment")
    for xi in (-6,.952,12):
        line,=axes[0,0].plot(t,1000*np.array([r[f"eta_x_{xi:g}m"] for r in rows]),label=f"x = {xi:g} m")
        axes[0,0].plot(t,1000*.05*np.cos(K*xi-OMEGA*t),"--",color=line.get_color(),alpha=.5)
    axes[0,0].set_ylabel("Surface elevation [mm]")
    axes[0,0].legend(fontsize=8)
    axes[0,1].plot(t,[r["interface_CFL"] for r in rows])
    axes[0,1].axhline(.5,color="tab:red",ls="--",label="safety limit")
    axes[0,1].set_ylabel("Interface CFL")
    axes[0,1].legend(fontsize=8)
    axes[1,0].plot(t,[r["pABS_min_Pa"]/1000 for r in rows])
    axes[1,0].set_ylabel("Minimum absolute pressure [kPa]")
    axes[1,1].semilogy(t,[r["mass_relative"] for r in rows],label="mass balance")
    axes[1,1].axhline(1e-4,color="tab:red",ls="--",label="safety limit")
    axes[1,1].set_ylabel("Relative mass imbalance")
    axes[1,1].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
        ax.set_xlabel("Physical time [s]")
    fig.savefig(out/"WAVE_DIAGNOSTIC.png",dpi=180)
    plt.close(fig)
    return stats

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--status",choices=("DIAGNOSTIC","FAILED","ACCEPTED"),default="DIAGNOSTIC")
    parser.add_argument("--mesh-id",required=True)
    parser.add_argument("--legacy-wave-review",action="store_true")
    args=parser.parse_args()
    trajectory=export(args.run,args.out,args.status,args.mesh_id)
    if args.legacy_wave_review:
        print(json.dumps(diagnostic(args.run,args.out,trajectory),indent=2))


