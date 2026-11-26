"""Repeatability and single-frequency identification for the Mini wave/flap case."""
import csv
import math
from pathlib import Path

import numpy as np

import wave_phase_map_campaign as campaign
from resume import c, D
from wave_phase_map_campaign import DT

TABLE = D/"WAVE_PHASE_TO_FLAP_DEG.csv"
REPORT = D/"WAVE_PHASE_TO_FLAP_REPORT.json"

def read_samples(stage, filename):
    for segment in campaign.STATE_DATA["segments"]:
        if segment["stage"]!=stage:
            continue
        for row in c.tail(Path(segment["folder"])/filename):
            if float(row["time_s"])<=segment["end_s"]+1e-9:
                yield row

def fit(rows,start,end,key,omega):
    samples=[(float(row["time_s"]),float(row[key])) for row in rows
             if start<=float(row["time_s"])<end]
    if len(samples)<.99*(end-start)/DT:
        raise RuntimeError(f"Incomplete {key} history for {start:.6f} to {end:.6f} s")
    t,y=np.asarray(samples).T
    if not np.isfinite(y).all() or np.max(abs(np.diff(t)-DT))>1e-8:
        raise RuntimeError(f"Nonfinite samples or physical time gap in {key}")
    phase=omega*(t-campaign.ORIGIN)
    design=np.column_stack((np.ones(len(t)),np.cos(phase),np.sin(phase)))
    mean,cosine,sine=np.linalg.lstsq(design,y,rcond=None)[0]
    return float(mean),complex(cosine,-sine)

def cycles(rows,start,period,key):
    return [fit(rows,start+i*period,start+(i+1)*period,key,2*math.pi/period)
            for i in range(campaign.CYCLES)]

def cycle_change(values):
    means,amplitudes=zip(*values)
    return dict(mean_relative=max(abs(b-a)/max(abs(a),1e-10) for a,b in zip(means,means[1:])),
                fundamental_relative=max(abs(b-a)/max(abs(a),abs(b),1e-10) for a,b in
                                         zip(amplitudes,amplitudes[1:])))

def repeatable(lift,drag):
    return all(v["mean_relative"]<=.01 and v["fundamental_relative"]<=.15 for v in
               (cycle_change(lift),cycle_change(drag)))

def identify(base,active,angles,incident):
    gains=[(lift-base)/angle for (_,lift),(_,angle) in zip(active,angles)]
    gain=sum(gains)/len(gains)
    if abs(gain)<1e-4 or max(abs(g/gain-1) for g in gains)>.2:
        raise RuntimeError("Flap-to-lift gain is weak or varies across cycles")
    # Relative to the phase of the crest at the upstream gauge.
    return -base/gain*np.exp(-1j*np.angle(incident)),gain

def finish_fixed_and_run_active(source,t,history):
    fixed="PHASE_MAP_WAVE_FIXED"
    active="PHASE_MAP_WAVE_ACTIVE_I1DEG"
    receipt=c.read(source.parent/"STOKES_AFTER_FINAL_STEP.json")
    period=float(receipt["native_period_s"])
    initial=c.read(source.parent/"STOKES_READBACK.json")
    if (initial["wave_type"]!="FifthOrderVofWave" or initial["advancing_direction"]!="+X"
            or abs(float(initial["wavelength_m"])-10)>1e-8 or abs(float(initial["current_m_s"])-18)>1e-8
            or abs(float(initial["native_period_s"])-period)>1e-8
            or abs(period-campaign.PERIOD)>DT or abs(float(receipt["height_m"])-.10)>1e-5):
        raise RuntimeError("Native Stokes V readbacks disagree with the planned wave")
    start=campaign.START_GATE
    end=start+campaign.CYCLES*period
    if t<end-DT:
        raise RuntimeError("Missing full WAVE/FIXED observation cycles")
    hist=list(read_samples(fixed,"history.csv"))
    gauge=list(read_samples(fixed,"gauges.csv"))
    checks={}
    refs={}
    for x,amp_tol in ((-3,.15),(.952,.25)):
        rows=[r for r in gauge if abs(float(r["x_m"])-x)<1e-7]
        measured=cycles(rows,start,period,"eta_actual_m")
        theory=cycles(rows,start,period,"eta_native_theory_m")
        if min(abs(v) for _,v in measured+theory)<1e-5:
            raise RuntimeError(f"Missing wave oscillation at x={x}")
        ratios=[a[1]/b[1] for a,b in zip(measured,theory)]
        error=max(abs(abs(r)-1) for r in ratios)
        phase=max(abs(math.degrees(np.angle(r))) for r in ratios)
        repeat=cycle_change(measured)["fundamental_relative"]
        checks[str(x)]=dict(amplitude_error=error,phase_error_deg=phase,
                            complex_repeatability=repeat,pass_gate=error<=amp_tol and phase<=20 and repeat<=.15)
        refs[x]=sum(a[1] for a in measured)/len(measured)
    fixed_cl=cycles(hist,start,period,"CL")
    fixed_cd=cycles(hist,start,period,"CD")
    passes=all(x["pass_gate"] for x in checks.values()) and repeatable(fixed_cl,fixed_cd)
    gate=dict(passed=passes,period_s=period,window_s=[start,end],gauges=checks,
              forces={"CL":cycle_change(fixed_cl),"CD":cycle_change(fixed_cd)},
              fixed_checkpoint=str(source),fixed_checkpoint_sha256=c.sha(source))
    campaign.status(operation="FIXED_REPEATABILITY_EVALUATED",period_s=period,fixed_gate=gate)
    if not passes:
        raise RuntimeError("WAVE/FIXED gauge or force repeatability gate failed; ACTIVE remains on HOLD")

    campaign.MACRO=D/"phase_identification_macro/MiniVofStokes.java"
    active_start=t
    _,end_active,_=campaign.integrate(active,source,t,history,math.ceil(4*period/DT),moving=True,
        options=dict(phase_identification=True,harmonic_flap_deg=1,
                     encounter_period_s=period,motion_origin_s=t,motion_ramp_s=period,
                     flow_cycle=False,af_branch_history=False,save_interval_s=.10))
    finish_active(active_start,end_active,period,fixed_cl,fixed_cd,refs[-3],gate)


def finish_active(active_start,end_active,period,fixed_cl,fixed_cd,incident,gate):
    active="PHASE_MAP_WAVE_ACTIVE_I1DEG"
    start=active_start+period
    active_hist=list(read_samples(active,"history.csv"))
    active_gauge=[row for row in read_samples(active,"gauges.csv") if abs(float(row["x_m"])+3)<1e-7]
    active_eta=cycles(active_gauge,start,period,"eta_actual_m")
    active_cl=cycles(active_hist,start,period,"CL")
    active_cd=cycles(active_hist,start,period,"CD")
    active_angles=cycles(active_hist,start,period,"delta_measured_deg")
    if any(abs(a/incident-1)>.15 for _,a in active_eta):
        raise RuntimeError("Incident wave changed between FIXED and ACTIVE")
    if any(abs(abs(a)-1)>.04 or abs(mean)>.04 for mean,a in active_angles):
        raise RuntimeError("Measured flap motion is not the specified 1 degree sinusoid")
    if not repeatable(active_cl,active_cd):
        raise RuntimeError("ACTIVE force response is not repeatable")

    base_mean=float(np.mean([mean for mean,_ in fixed_cl]))
    base=sum(amp for _,amp in fixed_cl)/campaign.CYCLES
    z,gain=identify(base,active_cl,active_angles,incident)
    if abs(z)>2:
        raise RuntimeError("Predicted compensation exceeds the qualified 2 degree range")
    report=dict(status="FIRST_HARMONIC_MAP_DIAGNOSTIC",phase_reference="Upstream gauge x=-3 m, crest at 0 degrees",
                period_s=period,dt_s=DT,flap_amplitude_deg=float(abs(z)),
                phase_offset_deg=float(np.degrees(np.angle(z))),
                delta_expression="amplitude_deg * cos(wave_phase_rad + phase_offset_rad)",
                fixed_CL_mean=base_mean,fixed_CL_first_harmonic=abs(base),active_end_s=end_active,
                flap_gain_CL_per_deg=abs(gain),flap_gain_phase_deg=float(np.degrees(np.angle(gain))),
                fixed_CD_mean=float(np.mean([mean for mean,_ in fixed_cd])),
                identification_CD_mean=float(np.mean([mean for mean,_ in active_cd])),
                mean_trim_included=False,closed_loop_or_map_test_done=False,fixed_gate=gate)
    with TABLE.open("x",newline="",encoding="utf-8") as file:
        writer=csv.writer(file)
        writer.writerow(("incident_wave_phase_deg","recommended_flap_deg_zero_mean"))
        for phi in range(361):
            writer.writerow((phi,float(np.real(z*np.exp(1j*np.radians(phi))))))
    c.coex.save(REPORT,report)
    campaign.status(operation="MAP_WRITTEN",phase_map=str(TABLE),map_report=str(REPORT))
