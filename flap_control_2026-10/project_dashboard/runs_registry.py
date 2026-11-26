"""Read-only dynamic run registry for CFD Live and Validation Lab.
Controller metadata is the discovery authority. Distinct experiment_id segments
merge by physical time; otherwise each run_id remains separately identifiable.
Uses shared stable file snapshots and PID checks from ramp_live.
"""
from __future__ import annotations
import csv, datetime as dt, io, math, statistics, threading, time
from pathlib import Path
import ramp_live

CAMP=ramp_live.CAMP
CASE_ROOT=CAMP/"cases"
# Explicitly allow controller-owned diagnostic runs relocated beneath the project root.
# This is a read-only allowlist, not arbitrary paths from controller JSON.
DIAGNOSTIC_ROOT=CAMP.parent/"independent_cfd_diagnostics"
ALLOWED_ROOTS=(CASE_ROOT,DIAGNOSTIC_ROOT)
MAX_JOBS=800
MAX_HISTORY_BYTES=18_000_000
MAPPING={
 "step": ("step","TimeStep","Step"),"t":("time_s","Physical Time (s)","Time","time"),
 "CL":("CL_hydro","CL_hydrodynamic","CL_total","CL","CL_mean"),
 "CD":("CD","CD_total","CD_mean"),
 "Fx":("Fx_N","Fx","Fx_half (N)"),
 "Fz":("Fz_N","Fz","Fz_half (N)"),
 "Mh":("Mh_Nm","moment_Nm"),
 "angle":("measured_angle_deg","flap_angle_deg","angle_deg"),
 "rate":("flap_angular_velocity_deg_s","angular_rate_deg_s"),
 "pabs":("p_absolute_min_Pa","pabs_min_Pa"),
 "mass":("mass_imbalance_relative",),
 "orphan":("overset_error_cells",),
 "quality":("min_cell_quality",),
 "iteration":("native_iteration","iteration"),
 "dt":("dt_s",),
 "cav":("cavitation_margin_Pa",),
 "k_floor":("k_floor_cells",),
 "omega_floor":("omega_floor_cells",),
}
_MEM={}
_LOCK=threading.Lock()

def is_controller_case(path):
    if not isinstance(path,str) or not path:
        return None
    try:
        folder=Path(path).resolve(strict=False)
        for allowed in ALLOWED_ROOTS:
            root=allowed.resolve(strict=False)
            if folder.is_relative_to(root) and folder!=root:
                return folder
        return None
    except (ValueError,OSError):
        return None

def get_jobs(queue=None):
    queue=ramp_live.read_json(ramp_live.QUEUE) if queue is None else queue
    if not isinstance(queue,dict):return [],None,{}
    items=queue.get("jobs") if isinstance(queue.get("jobs"),dict) else {}
    active=queue.get("active") if isinstance(queue.get("active"),dict) else None
    # Keep the most recent controller records when the queue archive grows.
    records=list(items.values())[-MAX_JOBS:]
    if active:records.append(active)
    eligible=[]
    for job in records:
        if not isinstance(job,dict):continue
        folder=is_controller_case(job.get("output"))
        if not folder:continue
        hist=folder/"history.csv"
        try:
            info=hist.stat()
            if info.st_size<35 or info.st_size>MAX_HISTORY_BYTES:continue
        except OSError:continue
        eligible.append(dict(job, _folder=str(folder), _history=str(hist),
                            _size=info.st_size,_mtime=info.st_mtime))
    # Active copy overrides original job's state by folder if the controller has it.
    uniq={}
    for j in eligible:uniq[str(j["_folder"]).lower()]=j
    return list(uniq.values()), active, queue

def run_key(job):
    exp=job.get("experiment_id")
    if isinstance(exp,str) and exp.strip():
        return "exp:"+exp.strip()
    rid=job.get("run_id")
    if isinstance(rid,str) and rid.strip():
        return "run:"+rid.strip()
    ident=job.get("id")
    return "job:"+str(ident or Path(job["_folder"]).name)

def groups(queue=None):
    jobs, active, state=get_jobs(queue)
    allruns={}
    for job in jobs:
        key=run_key(job)
        allruns.setdefault(key,[]).append(job)
    for key in allruns:
        allruns[key].sort(key=lambda x:(str(x.get("at") or ""),str(x.get("run_id") or "")))
    return allruns, active, state

def read_history_file(path):
    b=ramp_live.stable_bytes(Path(path),MAX_HISTORY_BYTES)
    if b is None:return []
    try:
        s=b.decode("utf-8-sig")
        if not s.endswith(("\r","\n")):
            s=s.rsplit("\n",1)[0]+"\n" if "\n" in s else ""
        return [r for r in csv.DictReader(io.StringIO(s)) if r and None not in r]
    except (UnicodeError,ValueError,csv.Error):
        return []

def compact(raw,path,segment):
    t=ramp_live.get(raw,*MAPPING["t"])
    if t is None:return None
    r={key:ramp_live.get(raw,*aliases) for key,aliases in MAPPING.items()}
    r["source"]=path
    r["segment"]=segment
    r["phase"]=str(raw.get("phase") or "") or None
    r["stage"]=ramp_live.get(raw,"stage")
    r["U"]=ramp_live.get(raw,"U_m_s")
    r["measurement_eligible"]=str(raw.get("measurement_eligible") or "").lower()=="true" if "measurement_eligible" in raw else None
    return r

def merged_history(segments,full=True):
    sample={}
    details=[]
    for item in segments:
        path=item["_history"]
        rows=read_history_file(path)
        added=0
        for line in rows:
            entry=compact(line,path,str(item.get("id") or item.get("run_id") or Path(path).parent.name))
            if entry is None:continue
            # Numerical physical time is the unique sample identity after restarts.
            # Later controller segment wins when physical times overlap.
            sample[round(entry["t"],9)]=entry
            added+=1
        details.append({"id":item.get("id"),"run_id":item.get("run_id"),"state":item.get("state"),
                        "at":item.get("at"),"path":path,"rows":added,
                        "modified_at":dt.datetime.fromtimestamp(item["_mtime"],dt.timezone.utc).isoformat()})
    ordered=sorted(sample.values(),key=lambda r:r["t"])
    count=len(ordered)
    if full and count>4000:
        stride=math.ceil(count/4000)
        reduced=ordered[::stride]
        if reduced[-1] is not ordered[-1]:reduced.append(ordered[-1])
        ordered=reduced
    return ordered,count,details

def statistics_for(rows,field,n=25):
    vals=[r for r in rows if r.get(field) is not None]
    cur=vals[-n:]
    if not cur:return None
    readings=[r[field] for r in cur]
    return {"mean":statistics.fmean(readings),"min":min(readings),"max":max(readings),
            "n":len(readings),"from_s":cur[0]["t"],"to_s":cur[-1]["t"],
            "source":cur[-1]["source"]}

def status_for(segments,active=None):
    newest=segments[-1]
    state=str(newest.get("state") or "").lower()
    approved=any(
        isinstance(j.get("macro_status"),dict) and
        (j["macro_status"].get("scientific_approved") is True or
         j["macro_status"].get("scientific_approval") is True)
        for j in segments)
    if state in ("failed","error","crashed"):
        return "FAILED"
    isactive=bool(active and active.get("output")==newest.get("output") and
                  str(active.get("state") or "").lower() in ("active","running"))
    if isactive:
        fresh=time.time()-newest["_mtime"]<65
        if fresh and ramp_live.pid_alive(active.get("pid")):
            return "ACTIVE"
        return "STALE" if not fresh else "DIAGNOSTIC"
    if approved:return "ACCEPTED"
    return "DIAGNOSTIC"

def descriptor(key,segments,active,read_stats=True):
    last=segments[-1]
    hist,count,details=merged_history(segments,full=False)
    current=hist[-1] if hist else {}
    status=status_for(segments,active)
    label=str(last.get("experiment_id") or last.get("id") or last.get("run_id") or key)
    if len(label)>75:label=label[:72]+"…"
    return {
        "id":key,"label":label,
        "status":status,"is_active":status=="ACTIVE",
        "category":status,"run_id":last.get("run_id"),
        "experiment_id":last.get("experiment_id"),"macro":last.get("macro"),
        "count":count,"segments":len(segments),"segment_ids":[j.get("id") for j in segments],
        "last_time_s":current.get("t"),"last_step":current.get("step"),
        "last_updated_at":dt.datetime.fromtimestamp(last["_mtime"],dt.timezone.utc).isoformat(),
        "source":last["_history"],"sources":[j["_history"] for j in segments],
        "stats":{k:statistics_for(hist,k) for k in ("CL","CD","Fx","Fz","Mh")} if read_stats else {},
        "scientific_approved":status=="ACCEPTED",
        "message":("Controller ended with failure. Recorded samples retained." if status=="FAILED" else
                   "Diagnostic unless explicit scientific approval is recorded."),
        "raw_state":last.get("state"),
        "provenance":details
    }

def list_runs(queue=None):
    allruns,active,_=groups(queue)
    result=[]
    for key,segments in allruns.items():
        result.append(descriptor(key,segments,active))
    result.sort(key=lambda d:(d["last_updated_at"],d["id"]),reverse=True)
    return result

def fetch_series(key,queue=None):
    allruns,active,_=groups(queue)
    if key not in allruns:return None
    seg=allruns[key]
    head=descriptor(key,seg,active)
    hist,count,details=merged_history(seg)
    head.update({"history":hist,"count":count,"provenance":details,
                 "window":"last 25 complete native samples per metric",
                 "residuals":{},"gauges":[]})
    return head

def manifest(static):
    # Controller's explicit active job is the authority, even after later
    # experiments replace an older failed ramp. Keep one consistent queue read.
    queue=ramp_live.read_json(ramp_live.QUEUE)
    rows=list_runs(queue=queue)
    active=queue.get("active") if isinstance(queue,dict) else None
    active_id=(run_key(active) if isinstance(active,dict) and
               is_controller_case(active.get("output")) else None)
    known_ids={row["id"] for row in rows}
    if active_id not in known_ids:active_id=None
    combined=[]
    for i in static:
        combined.append({"id":i["id"],"label":i["label"],"status":i["status"],
                         "count":i.get("count"),"last_time_s":i.get("last_time_s"),
                         "source":i.get("source"),"segments":1,
                         "is_static_reference":True})
    combined+=rows
    return {"runs":combined,"total":len(combined),"dynamic_count":len(rows),
            "active_run_id":active_id,
            "active_controller_state":(active.get("state") if active else None),
            "queue_state":(queue.get("queue_state") if isinstance(queue,dict) else None),
            "updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"read_only":True}
