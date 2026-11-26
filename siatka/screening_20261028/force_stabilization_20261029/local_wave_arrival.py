"""Operational near-foil wave-arrival exclusion; standard library, no solver actions.
This is not a wave-height, reflection, mesh/time or force-accuracy acceptance test.
Absolute CFD times are retained. The caller persists the first established origin.
"""
import bisect,csv,itertools,math,statistics
from pathlib import Path

STATIONS=(-1.0,2.5)
N=256
LIMITS={"signal_fraction":0.5,"fundamental_variance_fraction":0.70,
        "amplitude_pct":5.0,"mean_H_fraction":0.02,"waveform_rms_pct":10.0,
        "phase_deg":5.0,"period_relative":0.05}
def _finite(x):
 try:
  y=float(x)
  return y if math.isfinite(y) else None
 except (TypeError,ValueError):
  return None
def _wrap(x):return (x+180.0)%360.0-180.0
def _result(reason,**evidence):
 return dict(established=False,analysis_origin_s=None,reason=reason,
             operational_gate_only=True,accuracy_admitted=False,evidence=evidence)
def _load(path):
 data={x:{} for x in STATIONS};issues=[]
 try:
  with path.open(encoding="utf-8-sig",newline="") as f:
   reader=csv.DictReader(f)
   required={"time_s","x_m","eta_actual_m","eta_analytic_m"}
   if not required.issubset(reader.fieldnames or []):
    return None,["Required gauge CSV columns missing"]
   for number,row in enumerate(reader,2):
    x=_finite(row.get("x_m"));t=_finite(row.get("time_s"))
    station=next((z for z in STATIONS if x is not None and abs(x-z)<=1e-8),None)
    if station is None:continue
    if t is None:
     issues.append("Non-finite required-station time at row "+str(number));continue
    value=(_finite(row.get("eta_actual_m")),_finite(row.get("eta_analytic_m")))
    key=round(t,10)
    old=data[station].get(key)
    if old is not None and old[1:]!=value:
     issues.append("Conflicting duplicate at station "+str(station)+" time "+str(t))
    data[station][key]=(t,*value)
 except (OSError,csv.Error,UnicodeError) as ex:
  return None,[str(ex)]
 return {x:sorted(v.values()) for x,v in data.items()},issues
def _interpolate(rows,t,tol):
 ts=[v[0] for v in rows]
 i=bisect.bisect_left(ts,t)
 if i<len(rows) and abs(ts[i]-t)<=tol:return rows[i][1:]
 if i and abs(ts[i-1]-t)<=tol:return rows[i-1][1:]
 if i==0 or i==len(rows):return None
 a,b=rows[i-1],rows[i]
 if any(v is None for v in a[1:]+b[1:]):return None
 f=(t-a[0])/(b[0]-a[0])
 return tuple(a[j]+f*(b[j]-a[j]) for j in (1,2))
def _feature(values):
 mean=statistics.fmean(values);center=[v-mean for v in values]
 a=2*sum(v*math.cos(2*math.pi*j/N) for j,v in enumerate(center))/N
 b=2*sum(v*math.sin(2*math.pi*j/N) for j,v in enumerate(center))/N
 amp=math.hypot(a,b);variance=statistics.fmean(v*v for v in center)
 return dict(mean=mean,amplitude=amp,phase_deg=math.degrees(math.atan2(b,a)),
             fundamental_variance_fraction=min(1.0,amp*amp/(2*variance)) if variance>0 else 0.0,
             centered=center)
def _cycle(rows,start,T,H,spacing):
 tol=max(1e-9,T*1e-7);end=start+T;ts=[r[0] for r in rows]
 if not rows or ts[0]>start+tol or ts[-1]<end-tol:
  return None,"Incomplete endpoint coverage"
 lo=max(0,bisect.bisect_right(ts,start)-1)
 hi=min(len(rows),bisect.bisect_left(ts,end)+1)
 local=rows[lo:hi]
 if len(local)<2 or any(v is None for row in local for v in row[1:]):
  return None,"Non-finite actual/reference sample"
 maxgap=max(b[0]-a[0] for a,b in zip(local,local[1:]))
 allowed=min(1.5*spacing,min(.02,T/64))+tol
 if maxgap>allowed:return None,"Sampling gap or inadequate resolution"
 values=[_interpolate(local,start+j*T/N,tol) for j in range(N)]
 if any(v is None for v in values):return None,"Unbracketed interpolation"
 actual=[v[0] for v in values];reference=[v[1] for v in values]
 f=_feature(actual);ref=_feature(reference)
 if ref["amplitude"]<=max(1e-12,1e-6*H):return None,"Analytic fundamental absent"
 floor=max(.5*ref["amplitude"],.10*H)
 if f["amplitude"]<floor:return None,"Actual wave signal below threshold"
 if f["fundamental_variance_fraction"]<.70:return None,"Actual wave is not coherent at native period"
 f.update(reference_amplitude=ref["amplitude"],signal_threshold=floor,values=actual,
          start_s=start,end_s=end,actual_source_samples=sum(start-tol<=r[0]<=end+tol for r in local),
          maximum_sample_gap_s=maxgap)
 return f,None
def _frequency_fit(values,T):
 # Fit intercept+sin+cos; no phase adjustment is applied to waveform comparisons.
 n=len(values);ym=statistics.fmean(values);y=[v-ym for v in values]
 yy=sum(v*v for v in y);dt=T/N;best=None
 if yy<=0:return None
 for k in range(61):
  ratio=.85+.005*k;omega=2*math.pi*ratio/T
  c=[math.cos(omega*j*dt) for j in range(n)]
  s=[math.sin(omega*j*dt) for j in range(n)]
  cm=statistics.fmean(c);sm=statistics.fmean(s)
  c=[v-cm for v in c];s=[v-sm for v in s]
  cc=sum(v*v for v in c);ss=sum(v*v for v in s);cs=sum(a*b for a,b in zip(c,s))
  cy=sum(a*b for a,b in zip(c,y));sy=sum(a*b for a,b in zip(s,y))
  det=cc*ss-cs*cs
  if det<=1e-20:continue
  a=(cy*ss-sy*cs)/det;b=(sy*cc-cy*cs)/det
  score=(a*cy+b*sy)/yy
  if best is None or score>best["explained_variance"]:
   best=dict(period_s=T/ratio,frequency_ratio=ratio,explained_variance=score,boundary_optimum=k in (0,60))
 return best
def _pairs(features,H):
 result=[];passed=True
 for i,j in itertools.combinations(range(3),2):
  a,b=features[i],features[j];den=max((a["amplitude"]+b["amplitude"])/2,.10*H)
  metrics=dict(cycles=[i,j],amplitude_pct=100*abs(a["amplitude"]-b["amplitude"])/den,
   mean_difference_m=abs(a["mean"]-b["mean"]),
   waveform_rms_pct=100*math.sqrt(statistics.fmean((x-y)**2 for x,y in zip(a["centered"],b["centered"])))/den,
   phase_difference_deg=abs(_wrap(a["phase_deg"]-b["phase_deg"])))
  ok=metrics["amplitude_pct"]<=5+1e-8 and metrics["mean_difference_m"]<=.02*H+1e-10 and metrics["waveform_rms_pct"]<=10+1e-8 and metrics["phase_difference_deg"]<=5+1e-8
  metrics["passed"]=ok;passed=passed and ok;result.append(metrics)
 return passed,result
def assess(folder,activation_time_s,period_s,height_m,wavelength_m,xmin_m):
 """Read folder/gauges.csv; return earliest passing 3-cycle block and fixed origin.
 Caller supplies the verified frozen native full-height period. U=18m/s is fixed
 by this campaign. This function neither launches a solver nor changes any file.
 """
 numbers=[_finite(v) for v in (activation_time_s,period_s,height_m,wavelength_m,xmin_m)]
 if any(v is None for v in numbers):return _result("Invalid non-finite policy input")
 activation,T,H,L,xmin=numbers
 if T<=0 or H<=0 or L<=0 or xmin>=min(STATIONS):return _result("Invalid geometry or non-positive wave input")
 c_safe=min(18.0,L/T)
 floor=activation+(max(STATIONS)-xmin)/c_safe+T
 first=math.ceil((floor-activation)/T-1e-10)
 path=Path(folder)/"gauges.csv";data,issues=_load(path)
 base=dict(gauge_file=str(path),activation_time_s=activation,frozen_period_s=T,height_m=H,
  wavelength_m=L,xmin_m=xmin,stations_m=list(STATIONS),estimated_exclusion_floor_s=floor,
  floor_is_measured_arrival=False,assumed_positive_current_m_s=18.0,c_safe_m_s=c_safe,
  first_candidate_cycle_index=first,limits=LIMITS,hard_cap_handled_by_caller=True)
 if data is None or issues:return _result("Gauge data read/conflict failure",**base,issues=issues)
 if any(len(data[x])<2 for x in STATIONS):return _result("Required near-foil station missing",**base)
 spacing={}
 for x in STATIONS:
  dt=[b[0]-a[0] for a,b in zip(data[x],data[x][1:]) if b[0]>a[0]]
  if not dt:return _result("No usable sampling interval",**base,station_m=x)
  spacing[x]=statistics.median(dt)
  if spacing[x]>min(.02,T/64)+max(1e-9,T*1e-7):
   return _result("Gauge sampling too coarse",**base,station_m=x,median_spacing_s=spacing[x])
 latest=min(data[x][-1][0] for x in STATIONS)
 last_complete=math.floor((latest-activation)/T+1e-7)-1
 base.update(latest_common_sample_s=latest,median_spacing_s={str(x):spacing[x] for x in STATIONS})
 if last_complete<first+2:return _result("Awaiting three complete post-exclusion gauge cycles",**base)
 cache={};failures=[]
 for k in range(first,last_complete+1):
  for x in STATIONS:cache[x,k]=_cycle(data[x],activation+k*T,T,H,spacing[x])
 for k in range(first,last_complete-1):
  block={};ok=True
  for x in STATIONS:
   entries=[cache[x,j] for j in range(k,k+3)]
   errors=[dict(cycle_index=k+i,reason=e[1]) for i,e in enumerate(entries) if e[1]]
   if errors:
    ok=False;block[str(x)]=dict(errors=errors);continue
   feats=[e[0] for e in entries];pairpass,metrics=_pairs(feats,H)
   fit=_frequency_fit([v for f in feats for v in f["values"]],T)
   periodpass=fit is not None and not fit["boundary_optimum"] and abs(fit["period_s"]/T-1)<=.05+1e-10
   block[str(x)]=dict(cycles=[{z:v for z,v in f.items() if z not in ("values","centered")} for f in feats],
                     pair_metrics=metrics,frequency_fit=fit,period_pass=periodpass)
   ok=ok and pairpass and periodpass
  if ok:
   origin=activation+(k+3)*T
   return dict(established=True,analysis_origin_s=origin,reason="First three-cycle near-foil arrival block passed",
    operational_gate_only=True,accuracy_admitted=False,evidence=dict(**base,qualifying_cycle_indices=list(range(k,k+3)),
    qualifying_block_start_s=activation+k*T,qualifying_block_end_s=origin,stations=block,
    origin_policy="End of earliest passing block; caller persists once. Only subsequent force cycles eligible."))
  failures.append(dict(first_cycle_index=k,stations=block))
 return _result("No complete three-cycle block satisfies measured arrival gate",**base,
                candidate_blocks_checked=len(failures),latest_failure=failures[-1] if failures else None)
