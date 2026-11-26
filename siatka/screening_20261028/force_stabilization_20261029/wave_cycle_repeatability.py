"""Practical periodic-force repeatability screen. Standard library only; no solver actions.
History time remains absolute. An explicit analysis origin can exclude calm/ramp/arrival stages.
This is not mesh/time accuracy, wave propagation, conservation or force validation.
"""
import argparse,bisect,csv,itertools,json,math,statistics
from pathlib import Path

POINTS=256
LEGACY_KEYS=("CD","CL_total")
EPSILON={"CD":1e-6,"CL_total":1e-5,"CL":1e-5}
LIMITS={"mean_pct":0.5,"amplitude_pct":2.0,"waveform_rms_pct":3.0,"phase_deg":2.0}

def _number(x):
 try:
  v=float(x)
  return v if math.isfinite(v) else None
 except (TypeError,ValueError):return None

def _basis(reference):
 """Validate an explicitly supplied correction; historical raw use is deliberate."""
 if reference is None:
  return LEGACY_KEYS,{"label":"Historical raw CL_total basis; buoyancy not subtracted","CL_definition":"historical_raw_CL_total","reference":None}
 if not isinstance(reference,dict) or reference.get("available") is not True:
  raise ValueError("A validated available force_reference is required for corrected CL")
 values={key:None if isinstance(reference.get(key),bool) else _number(reference.get(key)) for key in ("cl_offset","buoyancy_N","reference_force_N")}
 if any(value is None for value in values.values()) or values["reference_force_N"]<=0:
  raise ValueError("Force reference must contain finite offset/buoyancy and positive reference_force_N")
 expected=values["buoyancy_N"]/values["reference_force_N"]
 if not math.isfinite(expected) or abs(values["cl_offset"]-expected)>1e-10*max(1.,abs(expected)):
  raise ValueError("Force reference cl_offset disagrees with buoyancy_N/reference_force_N")
 summary={key:reference.get(key) for key in ("case","mesh_sha256","provenance_file","reason")}
 summary.update(available=True,**values)
 return ("CD","CL"),{"label":"Lift coefficient with constant buoyancy subtracted","CL_definition":"buoyancy_subtracted","reference":summary}

def _load(paths,keys=LEGACY_KEYS,force_reference=None):
 samples={};sample_times={};sources=[];invalid=[];conflicts=[];errors=[];observed=[]
 correct=None
 if force_reference is not None:
  from force_reference import correct_row
  correct=correct_row
 for item in paths:
  path=Path(item);count=0;valid=0
  try:
   with path.open(encoding="utf-8-sig",newline="") as handle:
    for row in csv.DictReader(handle):
     count+=1;t=_number(row.get("time_s",row.get("physical_time_s")))
     if t is None:
      errors.append({"source":str(path),"row":count,"reason":"Missing/non-finite time"})
      continue
     observed.append(t)
     if correct is not None:
      try:values=correct(dict(row),dict(force_reference))
      except (ValueError,TypeError,KeyError,ArithmeticError) as ex:
       invalid.append({"source":str(path),"row":count,"time_s":t,"reason":"Force-reference correction failed: "+type(ex).__name__});continue
      if not isinstance(values,dict) or values.get("cl_correction_available") is not True:
       invalid.append({"source":str(path),"row":count,"time_s":t,"reason":"Corrected lift unavailable"});continue
     else:values=row
     v={k:_number(values.get(k,values.get("CL") if k=="CL_total" else None)) for k in keys}
     if any(x is None for x in v.values()):
      invalid.append({"source":str(path),"row":count,"time_s":t,"reason":"Missing/non-finite coefficient"});continue
     valid+=1;key=round(t,9)
     if key in samples:
      old=samples[key]
      if any(abs(v[k]-old[k])>max(1e-10,1e-8*max(abs(v[k]),abs(old[k]))) for k in keys):
       conflicts.append({"time_s":t,"old":old,"new":v,"later_source":str(path)})
     samples[key]=v;sample_times[key]=t
   sources.append({"path":str(path),"rows":count,"valid_force_rows":valid})
  except (OSError,csv.Error) as ex:
   errors.append({"source":str(path),"reason":type(ex).__name__+": "+str(ex)})
 # Rounding identifies duplicate samples only; interpolation retains measured times.
 return {sample_times[k]:v for k,v in samples.items()},sources,invalid,conflicts,errors,observed

def _interpolate(times,values,t):
 i=bisect.bisect_left(times,t)
 if i<len(times) and abs(times[i]-t)<=1e-10:return values[i]
 if i==0 or i==len(times):raise ValueError("No bracket; extrapolation prohibited")
 ta,tb=times[i-1],times[i]
 return values[i-1]+(values[i]-values[i-1])*(t-ta)/(tb-ta)

def _cycle(number,period,times,series,nominal_dt,invalid_times,origin_s=0.0,keys=None):
 keys=tuple(series) if keys is None else tuple(keys)
 if not keys or any(key not in EPSILON or key not in series for key in keys):raise ValueError("Unsupported/missing cycle coefficient")
 lo=origin_s+(number-1)*period;hi=origin_s+number*period
 base={"cycle":number,"start_s":lo,"end_s":hi,"complete":False}
 if not times or times[0]>lo+1e-10 or times[-1]<hi-1e-10:
  return dict(base,reason="Incomplete interval; no extrapolation")
 if any(lo-1e-10<=t<=hi+1e-10 for t in invalid_times):
  return dict(base,reason="Non-finite force sample in interval")
 left=max(0,bisect.bisect_right(times,lo)-1)
 right=min(len(times)-1,bisect.bisect_left(times,hi))
 gaps=[times[i+1]-times[i] for i in range(left,right)]
 maxgap=max(gaps,default=0)
 if not nominal_dt or maxgap>2.5*nominal_dt+1e-10:
  return dict(base,reason="History gap exceeds 2.5 nominal steps",max_gap_s=maxgap)
 grid=[lo+j*period/POINTS for j in range(POINTS)]
 result=dict(base,complete=True,max_gap_s=maxgap,coefficients={})
 for key in keys:
  values=[_interpolate(times,series[key],t) for t in grid]
  mean=math.fsum(values)/POINTS
  centered=[v-mean for v in values]
  cosine=2*math.fsum(v*math.cos(2*math.pi*j/POINTS) for j,v in enumerate(centered))/POINTS
  sine=2*math.fsum(v*math.sin(2*math.pi*j/POINTS) for j,v in enumerate(centered))/POINTS
  result["coefficients"][key]={"mean":mean,"rms":math.sqrt(math.fsum(v*v for v in values)/POINTS),
   "fluctuation_rms":math.sqrt(math.fsum(v*v for v in centered)/POINTS),
   "fundamental_amplitude":math.hypot(cosine,sine),"half_peak_to_peak":(max(values)-min(values))/2,
   "fundamental_phase_deg":math.degrees(math.atan2(-sine,cosine)) if math.hypot(cosine,sine)>1e-30 else None,
   "phase_grid_values":values}
 return result

def _compare(cycles,key):
 vals=[c["coefficients"][key] for c in cycles];eps=EPSILON[key]
 sm=max([v["rms"] for v in vals]+[eps])
 sa=max([v["fundamental_amplitude"] for v in vals]+[v["half_peak_to_peak"] for v in vals]+[0.1*sm,eps])
 sw=max([v["fluctuation_rms"] for v in vals]+[0.1*sm,eps])
 phase_relevant=all(v["fundamental_amplitude"]>=0.1*sa and v["fundamental_phase_deg"] is not None for v in vals)
 pairs=[]
 for i,j in itertools.combinations(range(len(vals)),2):
  a,b=vals[i],vals[j]
  shape=math.sqrt(math.fsum(((x-a["mean"])-(y-b["mean"]))**2 for x,y in zip(a["phase_grid_values"],b["phase_grid_values"]))/POINTS)
  phase=abs((a["fundamental_phase_deg"]-b["fundamental_phase_deg"]+180)%360-180) if phase_relevant else None
  v={"cycles":[cycles[i]["cycle"],cycles[j]["cycle"]],"mean_pct":100*abs(a["mean"]-b["mean"])/sm,
   "fundamental_amplitude_pct":100*abs(a["fundamental_amplitude"]-b["fundamental_amplitude"])/sa,
   "half_peak_to_peak_pct":100*abs(a["half_peak_to_peak"]-b["half_peak_to_peak"])/sa,
   "waveform_rms_pct":100*shape/sw,"phase_deg":phase}
  v["pass"]=(v["mean_pct"]<=LIMITS["mean_pct"] and v["fundamental_amplitude_pct"]<=LIMITS["amplitude_pct"]
    and v["half_peak_to_peak_pct"]<=LIMITS["amplitude_pct"] and v["waveform_rms_pct"]<=LIMITS["waveform_rms_pct"]
    and (phase is None or phase<=LIMITS["phase_deg"]))
  pairs.append(v)
 maximum={k:max(p[k] for p in pairs) for k in ("mean_pct","fundamental_amplitude_pct","half_peak_to_peak_pct","waveform_rms_pct")}
 maximum["phase_deg"]=max(p["phase_deg"] for p in pairs) if phase_relevant else None
 return {"pass":all(v["pass"] for v in pairs),"normalization":{"mean_scale":sm,"amplitude_scale":sa,"waveform_scale":sw,"epsilon":eps},
  "phase_applicable":phase_relevant,"phase_note":"N/A when fundamental amplitude is below 10% of the amplitude normalization; this is a relevance filter, not a measured signal-to-noise ratio." if not phase_relevant else "Wrapped phase differences at fixed absolute wave phase; no realignment.",
  "worst_pair_metrics":maximum,"pairs":pairs}

def evaluate(history_paths,period,min_cycles=10,max_cycles=20,analysis_origin_s=0.0,force_reference=None):
 """Read histories and return JSON-safe assessment; never writes files or controls a solver.
 stop_recommended = stop_for_repeatability OR cap_reached. A cap stop requests review,
 not a claim of instability. Caller must also retain all separate physical/resource guards.
 """
 period=float(period)
 analysis_origin_s=float(analysis_origin_s)
 if not math.isfinite(analysis_origin_s) or analysis_origin_s<0:raise ValueError("analysis_origin_s must be finite and nonnegative")
 if not math.isfinite(period) or period<=0:raise ValueError("period must be finite and positive")
 if min_cycles<4 or max_cycles<min_cycles:raise ValueError("Require 4 <= min_cycles <= max_cycles")
 keys,basis=_basis(force_reference)
 if isinstance(history_paths,(str,Path)):history_paths=[history_paths]
 samples,sources,invalid,conflicts,errors,observed=_load(history_paths,keys,force_reference)
 times=sorted(samples);last=max(observed) if observed else None
 interval=statistics.median(b-a for a,b in zip(times,times[1:]) if b>a) if len(times)>1 else None
 completed=max(0,int(math.floor((last-analysis_origin_s+1e-10)/period))) if last is not None else 0
 minimum=last is not None and last+1e-10>=analysis_origin_s+min_cycles*period
 cap=last is not None and last+1e-10>=analysis_origin_s+max_cycles*period
 series={k:[samples[t][k] for t in times] for k in keys}
 cycles=[_cycle(n,period,times,series,interval,[x["time_s"] for x in invalid],analysis_origin_s,keys) for n in range(1,completed+1)]
 latest=cycles[-4:] if len(cycles)>=4 else cycles
 full=len(latest)==4 and all(c["complete"] for c in latest)
 first=latest[0]["start_s"] if latest else None
 relevant_conflicts=[x for x in conflicts if first is None or x["time_s"]>=first-1e-10]
 quality=not errors and not relevant_conflicts
 comparisons={k:_compare(latest,k) for k in keys} if full else {}
 repeatable=full and quality and all(v["pass"] for v in comparisons.values())
 passed=bool(minimum and repeatable)
 status=("repeatability_screen_pass" if passed else "cycle_cap_reached_review_required" if cap else
  "awaiting_minimum_10_cycles" if not minimum and min_cycles==10 else "awaiting_minimum_cycles" if not minimum else
  "insufficient_complete_cycle_data" if not full else "history_conflict_review_required" if not quality else "force_cycles_not_yet_repeatable")
 return {"schema_version":2,"method":"Practical four-cycle force-repeatability screen; not force-accuracy validation",
  "coefficient_keys":list(keys),"force_basis":basis["label"],"CL_definition":basis["CL_definition"],"force_reference":basis["reference"],
  "period_s":period,"wave_clock_origin_s":analysis_origin_s,"min_cycles":min_cycles,"max_cycles":max_cycles,
  "earliest_review_time_s":analysis_origin_s+min_cycles*period,"review_cap_time_s":analysis_origin_s+max_cycles*period,
  "observed_time_s":last,"elapsed_wave_periods":max(0.0,(last-analysis_origin_s)/period) if last is not None else None,
  "complete_cycle_count_on_wave_clock":completed,"valid_complete_cycles":[c["cycle"] for c in cycles if c["complete"]],
  "excluded_cycles":[{k:v for k,v in c.items() if k!="coefficients"} for c in cycles if not c["complete"]],
  "minimum_elapsed":minimum,"cap_reached":cap,"latest_four_complete":full,"history_quality_pass":quality,
  "repeatable_last_four":bool(repeatable),"stop_for_repeatability":passed,"stop_recommended":bool(passed or cap),
  "stop_reason":"four_cycle_repeatability_after_minimum" if passed else "20_cycle_review_cap" if cap and max_cycles==20 else "cycle_review_cap" if cap else None,
  "status":status,"accuracy_validated":False,"point_count_per_cycle":POINTS,"nominal_history_interval_s":interval,
  "thresholds":dict(LIMITS),"comparisons":comparisons,"last_four_cycles":latest,
  "history_sources":sources,"invalid_force_rows":invalid,"duplicate_conflicts":conflicts,"read_errors":errors,
  "limitations":["Practical thresholds proposed for this exploratory campaign, not a universal CFD standard or formal uncertainty estimate.",
   "Force repeatability does not establish grid/time accuracy, conservation, input-wave quality or reflection independence.",
   "The existing 0.01% inlet mass residual remains reported separately; the user's exploratory exception is not altered by this screen.",
   "Reaching the cycle cap without repeatability requests setup/flow diagnosis; it does not prove the setup is wrong or that a physical unsteady solution should be periodic.",
   "Merge only verified continuations with unchanged wave clock/settings. This function checks overlap values but cannot establish source identity.",
   "Arithmetic quadrature and harmonic analysis use the common 256-point phase grid. No phase alignment or detrending beyond subtracting each cycle mean is applied."]}

if __name__=="__main__":
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("histories",nargs="+");parser.add_argument("--period",type=float,required=True)
 parser.add_argument("--min-cycles",type=int,default=10);parser.add_argument("--max-cycles",type=int,default=20)
 args=parser.parse_args();print(json.dumps(evaluate(args.histories,args.period,args.min_cycles,args.max_cycles),indent=2,allow_nan=False))
