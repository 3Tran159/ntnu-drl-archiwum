"""NTNU Science Project Control Center: independent, strictly read-only data server.
No STAR API, solver executable, queue or campaign writes are used.
Python stdlib only. All application outputs stay in project_dashboard.
"""
from __future__ import annotations
import argparse
import csv
import ctypes
import datetime as dt
import io
import json
import logging
import math
import os
import re
import shutil
import socket
import statistics
import subprocess
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = Path(r"F:\ntnu\flap_control")
CAMP = ROOT / "hydro_validation_2606_20261102"
WAVE = Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102")
VALID = CAMP / "validation"
CASES = CAMP / "cases"
LOG = HERE / "server.log"
B0 = CASES / "SP_B_split0_fixed" / "b0_top_direction_20261103_053542"
C0 = CASES / "SP_C_split0_overset" / "c0_top_direction_20261103_050724"
A0 = CASES / "SP_A_original_singlephase"
PRE_W04 = WAVE / "PRE_W04_20261102"
K0 = CASES / "SP_C_split0_overset" / "kinematic_poc_20261103_083855"
W02 = WAVE / "runs" / "W02_20261102_094416_8e2e45"
W03 = WAVE / "runs" / "W03_20261102_093248_c85d49"
RUNS = {
    "B0": {"label": "B0 · Split / fixed", "path": B0 / "history.csv", "base": B0, "category": "DIAGNOSTIC"},
    "C0": {"label": "C0 · Corrected Overset", "path": C0 / "history.csv", "base": C0, "category": "DIAGNOSTIC"},
    "K0": {"label": "K0 · Motion / flow frozen", "path": K0 / "history.csv", "base": K0, "category": "KINEMATIC ONLY"},
    "A0": {"label": "A0 · Original foil", "path": A0 / "SP_A_complete_accepted_history.csv", "base": A0, "category": "STABILIZED"},
    "W02": {"label": "W02 · Unaccepted wave", "path": W02 / "history.csv", "base": W02, "category": "PENDING"},
    "W03": {"label": "W03 · Smoke test", "path": W03 / "history.csv", "base": W03, "category": "SMOKE TEST"},
    "W04pre": {"label": "PRE_W04 · Calm ramp", "path": PRE_W04 / "history.csv", "base": PRE_W04, "category": "EXTERNAL"},
}
for p in (HERE,):
    p.mkdir(exist_ok=True)
logging.basicConfig(filename=str(LOG), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
_seen_issues = {}
_lock = threading.RLock()
_cache = {"at": 0, "data": None}
_series_cache = {}
_cpu_prev = None
_progress_seen={"case":None,"t":None,"iteration":None,"advanced_at":0}
_ALLOWED_IMAGE_DIRS = [CAMP / "reports", A0, CASES / "SP_B_split0_fixed",
                       CASES / "SP_C_split0_overset", PRE_W04]
_IMAGE_EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg",
                     ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}

def issue(key, exc):
    """Log each distinct read failure at most once per 2 minutes."""
    now = time.time()
    with _lock:
        if now - _seen_issues.get(key, 0) >= 120:
            logging.warning("SOURCE %s: %s", key, exc)
            _seen_issues[key] = now

def stat_mtime(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None

def read_atomic(path, max_bytes=6_000_000):
    """Stable snapshot, no locks, no writes to producer files."""
    path = Path(path)
    for attempt in range(2):
        try:
            before = path.stat()
            if before.st_size > max_bytes:
                raise ValueError("source exceeds safe read cap")
            with path.open("rb") as f:
                data = f.read(max_bytes + 1)
            after = path.stat()
            if len(data) <= max_bytes and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
                return data
        except (OSError, ValueError) as exc:
            issue(str(path), exc)
            return None
        time.sleep(0.015)
    issue(str(path), "file changed during read")
    return None

def load_json(path, fallback=None):
    blob = read_atomic(path)
    if blob is None:
        return fallback
    try:
        return json.loads(blob.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        issue(str(path), exc)
        return fallback

def load_csv(path, max_points=1800):
    data = read_atomic(path, max_bytes=18_000_000)
    if data is None:
        return []
    try:
        txt = data.decode("utf-8-sig")
        if txt and not txt.endswith(("\n", "\r")):
            txt = txt.rsplit("\n", 1)[0] + "\n"
        rows = list(csv.DictReader(io.StringIO(txt)))
        if len(rows) > max_points:
            stride = max(1, math.ceil(len(rows) / max_points))
            rows = rows[::stride] + ([rows[-1]] if rows[-1] not in rows[::stride] else [])
        return rows
    except (ValueError, csv.Error, UnicodeError) as exc:
        issue(str(path), exc)
        return []

def number(v):
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def first_number(row, *names):
    for name in names:
        if name in row:
            r = number(row[name])
            if r is not None:
                return r
    return None

def compact_history(rows):
    out = []
    for row in rows:
        out.append({
            "step": first_number(row, "step", "TimeStep", "timestep", "Step"),
            "t": first_number(row, "time_s", "Time", "time", "Physical Time (s)"),
            "CL": first_number(row, "CL_hydro", "CL_hydrodynamic", "CL_total", "CL", "cl", "CL_mean"),
            "CD": first_number(row, "CD", "CD_total", "cd", "CD_mean"),
            "Fx": first_number(row, "Fx_N", "Fx", "Fx_half (N)"),
            "Fz": first_number(row, "Fz_N", "Fz", "Fz_half (N)"),
            "Mh": first_number(row, "Mh_Nm", "moment_Nm"),
            "pabs": first_number(row, "p_absolute_min_Pa"),
            "cav": first_number(row, "cavitation_margin_Pa"),
            "mass": first_number(row, "mass_imbalance_relative"),
            "dt": first_number(row, "dt_s"),
            "angle": first_number(row, "flap_angle_deg"),
            "measured_angle": first_number(row, "measured_deg"),
            "angle_error": first_number(row, "angle_error_deg"),
            "center_error": first_number(row, "center_error_m"),
            "angular_rate": first_number(row, "flap_angular_velocity_deg_s"),
            "flow_frozen":str(row.get("flow_frozen","")).lower()=="true",
            "face_validity":first_number(row,"min_face_validity"),
            "difficult_cells":first_number(row,"difficult_interpolation_cells"),
            "min_volume":first_number(row,"min_volume_m3"),
            "cfl":first_number(row,"max_CFL"),
            "interface_cfl":first_number(row,"interface_CFL"),
            "wave_target_h":first_number(row,"target_H_m"),
            "iteration": first_number(row, "native_iteration", "iteration"),
            "wallclock": first_number(row, "wall_clock_s"),
            "yplus": first_number(row, "yplus_mean"),
            "quality": first_number(row, "min_cell_quality"),
            "orphan": first_number(row, "overset_error_cells"),
        })
    return out

def field_stats(rows, key, n=25):
    good = [r for r in rows if r.get(key) is not None]
    window = good[-n:]
    if not window:
        return None
    vals = [r[key] for r in window]
    prev = good[-2*n:-n]
    pv = [r[key] for r in prev]
    avg = statistics.fmean(vals)
    prev_avg = statistics.fmean(pv) if pv else None
    return {
        "mean": avg, "min": min(vals), "max": max(vals),
        "std": statistics.pstdev(vals) if len(vals)>1 else 0,
        "n": len(vals), "from_s": window[0].get("t"), "to_s": window[-1].get("t"),
        "drift_pct": (avg-prev_avg)/abs(prev_avg)*100 if prev_avg and abs(prev_avg)>1e-15 else None,
        "range_pct": (max(vals)-min(vals))/abs(avg)*100 if avg else None
    }

def read_series(name):
    spec = RUNS.get(name)
    if not spec:
        return None
    path = spec["path"]
    now = time.time()
    with _lock:
        hit = _series_cache.get(name)
        mtime = stat_mtime(path)
        if hit and hit["mtime"] == mtime and now - hit["at"] < 10:
            return hit["data"]
    hist = compact_history(load_csv(path))
    residuals = {}
    base = spec["base"]
    if name in ("B0", "C0"):
        for p in sorted(base.glob("residual_final_*.csv")):
            key = p.stem.removeprefix("residual_final_")
            records = load_csv(p, max_points=320)
            try:
                pts = [{"x": first_number(x, "Iteration", "iteration"),
                        "y": first_number(x, key)} for x in records]
                residuals[key] = [p for p in pts if p["x"] is not None and p["y"] is not None]
            except Exception as exc:
                issue(str(p), exc)
    summary = {k: field_stats(hist, k) for k in ("CL", "CD", "Fx", "Fz", "Mh", "pabs", "mass", "cav", "angle","angular_rate","angle_error","center_error","quality","orphan","min_volume","cfl","interface_cfl")}
    gauges=[]
    if name in ("W02","W03"):
        for row in load_csv(base/"gauges.csv",max_points=7000):
            xpos=first_number(row,"x_m")
            ts=first_number(row,"time_s")
            eta=first_number(row,"eta_actual_m")
            if xpos is not None and abs(xpos-(-0.5))<1e-6 and ts is not None and eta is not None:
                gauges.append({"x":ts,"y":eta})
    result = {
        "id": name, "label": spec["label"], "category": spec["category"],
        "history": hist, "residuals": residuals, "gauges":gauges, "gauge_x_m":-0.5 if gauges else None, "stats": summary,
        "source": str(path), "mtime": mtime, "count": len(hist),
        "window": "last 25 valid CSV samples; K0 is frozen-flow kinematic geometry only; B/C quantitative results diagnostic",
    }
    with _lock:
        _series_cache[name] = {"mtime": mtime, "at": now, "data": result}
    return result

def read_reviews():
    results = []
    for p in sorted(VALID.glob("review_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
        doc = load_json(p, {})
        if not isinstance(doc, dict):
            continue
        last = doc.get("last") or {}
        means = doc.get("last25_means") or {}
        results.append({
            "id": p.stem,
            "at": doc.get("at"),
            "run": doc.get("run", ""),
            "scientific_approved": doc.get("scientific_approved") is True,
            "status": "ACCEPTED" if doc.get("scientific_approved") is True else "DIAGNOSTIC",
            "CL": first_number(means, "CL_hydro", "CL") or first_number(last, "CL_hydro", "CL"),
            "CD": first_number(means, "CD") or first_number(last, "CD"),
            "Mh": first_number(means, "Mh_Nm") or first_number(last, "Mh_Nm"),
            "guard_results": doc.get("whole_run_guards") or doc.get("strict_guards"),
            "source": str(p)
        })
    return results

def decision_timeline():
    path = CAMP / "NIGHT_DECISIONS.jsonl"
    data = read_atomic(path, max_bytes=12_000_000)
    if not data:
        return []
    lines = data.decode("utf-8-sig", errors="replace").splitlines()
    out = []
    for line in lines[-80:]:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        kind=str(rec.get("kind") or "")
        job=rec.get("job")
        joblabel=(job.get("id") or job.get("macro") or "") if isinstance(job,dict) else str(job or "")
        event=rec.get("decision") or rec.get("reason") or rec.get("summary") or rec.get("action") or " · ".join(x for x in (kind,joblabel,rec.get("macro") or "") if x)
        out.append({
            "at": rec.get("at") or rec.get("timestamp") or rec.get("time"),
            "decision": str(event or "Recorded event (no description)")[:500],
            "case": rec.get("case") or rec.get("variant") or "",
            "source": str(path)
        })
    return list(reversed(out))

def wave_sources():
    out = []
    for code in ("W01", "W02", "W03"):
        p = WAVE / "validations" / (code + ".json")
        obj = load_json(p)
        if isinstance(obj, dict):
            qualitative=obj.get("qualitative_NWAR_accepted") is True and obj.get("project_accepted") is True
            scientific=obj.get("scientific_NWAR_accepted") is True
            out.append({"id":code, "status":"QUALITATIVE PASS" if qualitative else str(obj.get("run_verification") or "PENDING").upper(),
                        "source": str(p), "details":"Qualitative NWAR "+("accepted" if qualitative else "not accepted")+
                                  " · quantitative "+("approved" if scientific else "not approved"),
                        "scientific_NWAR_accepted":scientific,"qualitative_NWAR_accepted":qualitative})
    pre = load_json(PRE_W04 / "state.json")
    if isinstance(pre, dict):
        out.append({"id":"PRE_W04", "status":str(pre.get("state") or pre.get("status") or "DATA AVAILABLE"),
                    "source":str(PRE_W04 / "state.json"), "details":"External calm-water wave preparation"})
    return out

def hardware():
    result={"cpu_percent":None, "cpu_temperature_C":None, "cpu_nominal_MHz":None,
            "ram_used_GB":None, "ram_total_GB":None,
            "gpu_percent":None, "vram_used_MB":None, "vram_total_MB":None,
            "gpu_temperature_C":None, "power_limiter":None,
            "disk":[], "star_processes":[], "mpi_ranks":None}
    global _cpu_prev
    try:
        class FILETIME(ctypes.Structure):
            _fields_=[("lo",ctypes.c_uint32),("hi",ctypes.c_uint32)]
        idle,kernel,user=FILETIME(),FILETIME(),FILETIME()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user)):
            def as_int(t):return (t.hi<<32)|t.lo
            current=(as_int(idle),as_int(kernel),as_int(user))
            with _lock:
                old=_cpu_prev
                _cpu_prev=current
            if old:
                di=current[0]-old[0]
                dk=current[1]-old[1]
                du=current[2]-old[2]
                denom=dk+du
                if denom>0:result["cpu_percent"]=round(max(0,min(100,100*(denom-di)/denom)),1)
    except (AttributeError,OSError):pass
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            result["cpu_nominal_MHz"]=winreg.QueryValueEx(key,"~MHz")[0]
    except (ImportError,OSError):pass
    try:
        class MEM(ctypes.Structure):
            _fields_=[("length",ctypes.c_ulong),("memory_load",ctypes.c_ulong),
                     ("total_phys",ctypes.c_ulonglong),("avail_phys",ctypes.c_ulonglong),
                     ("total_page",ctypes.c_ulonglong),("avail_page",ctypes.c_ulonglong),
                     ("total_virtual",ctypes.c_ulonglong),("avail_virtual",ctypes.c_ulonglong),
                     ("avail_extended_virtual",ctypes.c_ulonglong)]
        mem=MEM();mem.length=ctypes.sizeof(MEM)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            result["ram_total_GB"]=round(mem.total_phys/1e9,2)
            result["ram_used_GB"]=round((mem.total_phys-mem.avail_phys)/1e9,2)
    except (AttributeError, OSError): pass
    for drive in ("C:\\", "E:\\", "F:\\"):
        try:
            ds=shutil.disk_usage(drive)
            result["disk"].append({"name":drive[:2], "free_GB":round(ds.free/1e9,1),
                                   "total_GB":round(ds.total/1e9,1)})
        except OSError: pass
    try:
        cmd=["nvidia-smi","--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=2,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if cp.returncode==0 and cp.stdout.strip():
            fields=[number(x.strip()) for x in cp.stdout.strip().splitlines()[0].split(",")]
            if len(fields)==4:
                result.update(zip(("gpu_percent","vram_used_MB","vram_total_MB","gpu_temperature_C"),fields))
    except (OSError,subprocess.TimeoutExpired): pass
    try:
        cp=subprocess.run(["tasklist","/FO","CSV","/NH"], capture_output=True,text=True,timeout=3,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if cp.returncode==0:
            procs=list(csv.reader(io.StringIO(cp.stdout)))
            star=[r for r in procs if r and re.search(r"starccm|star-ccm|star\.exe",r[0],re.I)]
            mpi=[r for r in procs if r and re.search(r"^mpiexec|^hydra|^smpd",r[0],re.I)]
            result["star_processes"]=[{"name":r[0], "pid":r[1]} for r in star[:16]]
            result["mpi_ranks"]=len(mpi)
    except (OSError,subprocess.TimeoutExpired): pass
    return result

def get_image_index():
    pics={}
    for root in _ALLOWED_IMAGE_DIRS:
        if not root.is_dir(): continue
        try:
            for p in root.iterdir():
                if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS and p.stat().st_size<16_000_000:
                    key = re.sub(r"[^A-Za-z0-9_.-]","_",root.name + "__" + p.name)
                    pics[key] = p
        except OSError: continue
    return pics

def snapshot():
    now=time.time()
    with _lock:
        if _cache["data"] is not None and now-_cache["at"]<6:
            return _cache["data"]
    status=load_json(CAMP / "NIGHT_STATUS.json",{}) or {}
    queue=load_json(CAMP / "NIGHT_QUEUE.json",{}) or {}
    qstate=load_json(CAMP / "NIGHT_QUEUE_STATE.json",{}) or {}
    review=load_json(CAMP / "WORK_CURRENT_REVIEW.json",{}) or {}
    dashboard=load_json(CAMP / "NIGHT_DASHBOARD.json",{}) or {}
    paused=load_json(ROOT / "PAUSED_FOR_HOME.json")
    geom=load_json(CAMP / "geometry" / "current_geometry.json",{}) or {}
    mesh=load_json(VALID / "mesh_review_c0_tight_cage_v2_20261103_025110.json",{}) or {}
    b=read_series("B0")
    c=read_series("C0")
    hardware_data=hardware()
    stamps={nm:stat_mtime(path) for nm,path in {
        "status":CAMP/"NIGHT_STATUS.json", "queue":CAMP/"NIGHT_QUEUE_STATE.json",
        "review":CAMP/"WORK_CURRENT_REVIEW.json",
        "B0":B0/"history.csv", "C0":C0/"history.csv",
    }.items()}
    freshness=now-stamps["status"] if stamps["status"] else None
    has_star=bool(hardware_data.get("star_processes"))
    queue_status = str(status.get("queue_state") or "").upper()
    live=status.get("actual_live_metrics") or {}
    status_action=str(status.get("active_operation") or "").strip()
    status_native=str(status.get("solver_state") or "").upper()
    explicit_pause=bool(isinstance(paused,dict) and paused.get("requires_explicit_user_resume"))
    source_time=live.get("log_updated_at")
    try:
        last_log=dt.datetime.fromisoformat(source_time)
        if last_log.tzinfo is None:
            last_log=last_log.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        log_age=(dt.datetime.now(dt.timezone.utc)-last_log.astimezone(dt.timezone.utc)).total_seconds()
    except (TypeError,ValueError):
        log_age=None
    time_val=first_number(live,"physical_time_s","time_s")
    iter_val=first_number(live,"iteration","timestep")
    progress_case=str(status.get("active_input") or status.get("active_operation") or "")
    global _progress_seen
    with _lock:
        prev=_progress_seen
        if progress_case!=prev["case"]:
            _progress_seen={"case":progress_case,"t":time_val,"iteration":iter_val,"advanced_at":0}
        else:
            advanced=((time_val is not None and prev["t"] is not None and time_val>prev["t"]+1e-10)
                       or (iter_val is not None and prev["iteration"] is not None and iter_val>prev["iteration"]))
            if advanced:
                prev["advanced_at"]=now
            if time_val is not None:prev["t"]=time_val
            if iter_val is not None:prev["iteration"]=iter_val
        advanced_age=now-_progress_seen["advanced_at"] if _progress_seen["advanced_at"] else None
    progress_verified=(has_star and status_native=="RUNNING"
        and log_age is not None and -3<=log_age<25 and
        ((advanced_age is not None and advanced_age<50)
         or status.get("solver_actually_advancing") is True))
    if freshness is None:
        computed_state="OFFLINE"
        status_reason="Campaign status source unavailable or unreadable"
    elif freshness>180:
        computed_state="STALE"
        status_reason="Campaign status file is older than 180 seconds"
    elif explicit_pause or "PAUSED" in queue_status:
        computed_state="HOLD"
        status_reason="Explicit relocation pause; no solver intervention"
    elif "HOLD" in queue_status or status_native=="HOLD":
        computed_state="HOLD"
        status_reason="Main Work holding for scientific review; no new solver work authorized here"
    elif status_native=="FAILED" or "FAILED" in queue_status:
        computed_state="FAILED"
        status_reason="Failed state reported by campaign controller"
    elif not has_star or status_native=="STOPPED":
        computed_state="STOPPED" if freshness is not None and freshness<900 else "STALE"
        status_reason="No confirmed progressing STAR job"
    elif progress_verified:
        computed_state="RUNNING"
        status_reason=("Native process + fresh advancing kinematic output confirmed"
                       if status.get("current_job_kind")=="kinematic" else
                       "Native STAR process + progressing physical time/iterations confirmed")
    elif status_native=="RUNNING" and live.get("saving_or_exporting") is True and log_age is not None and 0<=log_age<20:
        computed_state="SAVING"
        status_reason="Fresh save/export evidence; active progress not yet reconfirmed"
    else:
        computed_state="HOLD"
        status_reason="A STAR process exists; progress not independently confirmed"
    bcl=b["stats"].get("CL") if b else None
    ccl=c["stats"].get("CL") if c else None
    bcd=b["stats"].get("CD") if b else None
    ccd=c["stats"].get("CD") if c else None
    def pct(a,base):
        return (a/base-1)*100 if a is not None and base not in (None,0) else None
    validation={
        "B0":{k:(b["stats"][k]["mean"] if b["stats"][k] else None) for k in ("CL","CD","Fx","Fz","Mh")},
        "C0":{k:(c["stats"][k]["mean"] if c["stats"][k] else None) for k in ("CL","CD","Fx","Fz","Mh")},
        "delta_CL_pct":pct(ccl["mean"] if ccl else None,bcl["mean"] if bcl else None),
        "delta_CD_pct":pct(ccd["mean"] if ccd else None,bcd["mean"] if bcd else None),
        "B_source":str(B0/"history.csv"), "C_source":str(C0/"history.csv"),
        "B_window":bcl and [bcl["from_s"],bcl["to_s"]],
        "C_window":ccl and [ccl["from_s"],ccl["to_s"]],
        "scientific_approved":False,
        "note":"0° diagnostic comparison only. Different physical-time windows; matching numerics/boundary and residual review pending. <1% proof-of-concept screen is not grid independence."
    }
    # Campaign may retain a B0 validation checkpoint while the latest C0 motion
    # checkpoint is held separately. Use source metadata only, never hash .sim.
    checkpoint=status.get("latest_owned_checkpoint") or status.get("last_checkpoint_integrity") or {}
    latest=checkpoint.get("path") or status.get("last_checkpoint")
    if not isinstance(review,dict): review={}
    view_review=status.get("work_review",{}) or {}
    kinematic=read_series("K0")
    kinlast=kinematic["history"][-1] if kinematic and kinematic["history"] else {}
    kin_status=live.get("macro_status") or {}
    kinematic_passed=(status.get("scientific_gates",{}).get("kinematic_sweep_accepted") is True
                       or (kin_status.get("status")=="kinematic_poc_passed"
                           and kin_status.get("hydrodynamics_solved") is False))
    if isinstance(review,dict):
        label=review.get("current_case_label")
    else:
        label=None
    active_case=(label or ("C0 · prescribed motion" if "Kinematic" in status_action else None))
    if kinematic_passed and not active_case:
        active_case="C0 · motion PoC / flow frozen"
    active_operation=status_action or "No operation"
    data={
        "server_time":dt.datetime.now(dt.timezone.utc).isoformat(),
        "state":computed_state, "reason":status_reason,
        "progress_verified":progress_verified, "log_age_s":round(log_age,1) if log_age is not None else None,
        "paused":explicit_pause,
        "source_status_at":status.get("at"), "source_age_s":round(freshness,1) if freshness is not None else None,
        "queue_state":queue_status, "actual_solver_state":status.get("solver_state"),
        "case":active_case if (active_case and (status_native=="RUNNING" or kinematic_passed)) else (status.get("last_solved_case") or "—"),
        "active_operation":active_operation,
        "last_solved_case":status.get("last_solved_case"),
        "physical_time_s":live.get("physical_time_s",status.get("physical_time_s")) if (status_native=="RUNNING" or kinematic_passed) else status.get("physical_time_s"),
        "iteration":live.get("iteration",status.get("iteration")) if (status_native=="RUNNING" or kinematic_passed) else status.get("iteration"),
        "timestep":live.get("timestep",status.get("timestep")) if (status_native=="RUNNING" or kinematic_passed) else status.get("timestep"),
        "checkpoint":latest,
        "checkpoint_verified":checkpoint.get("native_reopen_verified"),
        "checkpoint_complete":checkpoint.get("native_save_complete"),
        "checkpoint_bytes":checkpoint.get("bytes"),
        "decision":view_review.get("decision") or review.get("decision") or review.get("last_decision") or "",
        "obstacle":status.get("current_obstacle") or view_review.get("obstacle") or review.get("obstacle") or status.get("C0_bias_status") or "",
        "next":view_review.get("next") or review.get("next") or review.get("next_test") or "",
        "kinematic_gate":bool(status.get("scientific_gates",{}).get("C0_accepted_for_kinematics") is True),
        "kinematic_approval_evidence":status.get("scientific_gates",{}).get("kinematic_sweep_evidence"),
        "kinematic_passed":kinematic_passed,
        "kinematic": {"source":str(K0/"history.csv"),"steps":kinematic["count"] if kinematic else 0,
                      "motion_last":kinlast,"status":"KINEMATIC PASS" if kinematic_passed else (kin_status.get("status") or "RECORDED"),
                      "hydrodynamics_solved":False if kinematic_passed else kin_status.get("hydrodynamics_solved", None)},
        "phase":"KINEMATIC POC VERIFIED; HYDRO VALIDATION PENDING" if kinematic_passed else "STATIC / OVERSET VALIDATION",
        "scientific_gate":bool(status.get("scientific_gates",{}).get("C0_bias_explained_and_approved") is True),
        "training_approved":bool(status.get("training_approved") is True),
        "validation":validation, "geometry":geom,
        "mesh":mesh, "waves":wave_sources(),
        "hardware":hardware_data,
        "runs":[{"id":k,"label":v["label"],"rows":len(read_series(k)["history"]),
                 "source":str(v["path"]),"source_at":stat_mtime(v["path"])} for k,v in RUNS.items()],
        "images":[{"key":k, "name":p.name, "url":"/media/"+k} for k,p in get_image_index().items()],
        "status_file":str(CAMP/"NIGHT_STATUS.json"),
        "queue_file":str(CAMP/"NIGHT_QUEUE_STATE.json"),
        "review_file":str(CAMP/"WORK_CURRENT_REVIEW.json"),
        "timestamps":stamps,
        "sources": {"status":bool(status),"review":bool(review),"queue":bool(qstate),
                    "dashboard":bool(dashboard),"waves":WAVE.exists()},
        "note":"Source data are read-only. K0 is flow frozen, never force validation. Solver RUNNING is not inferred from historical JSON alone."
    }
    with _lock:
        _cache.update({"at":time.time(),"data":data})
    return data

class Handler(BaseHTTPRequestHandler):
    server_version="NTNU-ProjectMonitor/1.0"
    def log_message(self, fmt, *args):
        logging.info("%s %s", self.address_string(),fmt%args)
    def send_payload(self, body, mimetype="application/json; charset=utf-8", code=200):
        self.send_response(code)
        self.send_header("Content-Type", mimetype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command!="HEAD":
            self.wfile.write(body)
    def do_HEAD(self): self.do_GET()
    def do_GET(self):
        parsed=urlparse(self.path)
        path=parsed.path
        try:
            if path=="/api/runs":
                import runs_registry
                legacy=[{"id":k,"label":v["label"],"status":"DIAGNOSTIC",
                         "count":read_series(k)["count"],"last_time_s":(
                             read_series(k)["history"][-1]["t"] if read_series(k)["history"] else None),
                         "source":str(v["path"])} for k,v in RUNS.items()]
                return self.json(runs_registry.manifest(legacy))
            if path=="/api/run_series":
                import runs_registry
                rid=parse_qs(parsed.query).get("id",[""])[0]
                if rid in RUNS:
                    return self.json(read_series(rid))
                case=runs_registry.fetch_series(rid)
                return self.json(case) if case else self.err(404)
            if path=="/api/flow/manifest":
                import flow_field
                return self.json(flow_field.manifest())
            if path=="/api/flow/frame":
                import flow_field
                args=parse_qs(parsed.query)
                try:
                    fid=args.get("id",[""])[0]
                    roi=args.get("region",["foil"])[0]
                    return self.json(flow_field.frame_data(fid,roi))
                except ValueError:
                    return self.err(404)
            if path=="/api/flow/native":
                import flow_field
                args=parse_qs(parsed.query)
                pic=flow_field.native_image(args.get("id",[""])[0],args.get("view",[""])[0])
                if not pic:return self.err(404)
                blob=read_atomic(pic,max_bytes=7_000_000)
                if blob is None:return self.err(503)
                return self.send_payload(blob,"image/png")
            if path=="/api/ramp":
                import ramp_live
                return self.json(ramp_live.snapshot())
            if path=="/api/snapshot":
                return self.json(snapshot())
            if path=="/api/series":
                ident=parse_qs(parsed.query).get("id",["B0"])[0]
                payload=read_series(ident)
                return self.json(payload) if payload else self.err(404)
            if path=="/api/history":
                return self.json({"reviews":read_reviews(),"decisions":decision_timeline()})
            if path=="/api/health":
                return self.json({"service":"ok","read_only":True,"uptime_s":int(time.time()-self.server.started),"campaign_exists":CAMP.is_dir()})
            if path.startswith("/media/"):
                key=path[len("/media/"):]
                pic=get_image_index().get(key)
                if not pic:return self.err(404)
                try:
                    blob=read_atomic(pic, max_bytes=16_000_000)
                    if blob is None:return self.err(503)
                    return self.send_payload(blob,_IMAGE_EXTENSIONS[pic.suffix.lower()])
                except OSError:return self.err(503)
            if path in ("/","/index.html","/app.js","/styles.css","/ramp_live.js","/ramp_live.css","/flow_field.js","/flow_field.css","/runs_registry.css"):
                name="index.html" if path=="/" else path.lstrip("/")
                body=read_atomic(HERE/name, max_bytes=1_500_000)
                if body is None:return self.err(503)
                content_type={"index.html":"text/html; charset=utf-8",
                              "app.js":"application/javascript; charset=utf-8",
                              "styles.css":"text/css; charset=utf-8",
                              "ramp_live.js":"application/javascript; charset=utf-8",
                              "ramp_live.css":"text/css; charset=utf-8",
                              "flow_field.js":"application/javascript; charset=utf-8",
                              "flow_field.css":"text/css; charset=utf-8",
                              "runs_registry.css":"text/css; charset=utf-8"}[name]
                return self.send_payload(body,content_type)
            return self.err(404)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            logging.exception("API error %s",path)
            return self.err(500)
    def json(self, value):
        body=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")
        return self.send_payload(body)
    def err(self, code):
        return self.json_error(code,{"error":{404:"not found",503:"data temporarily unavailable",500:"internal error"}.get(code,"error")})
    def json_error(self,code,obj):
        return self.send_payload(json.dumps(obj).encode(),code=code)

def serve(host,port):
    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address=True
        daemon_threads=True
    http=ReuseServer((host,port),Handler)
    http.started=time.time()
    logging.info("Serving on %s:%s",host,port)
    print("NTNU Project Control Center: http://%s:%s" % (host,port),flush=True)
    return http

def tailscale_ip():
    try:
        cp=subprocess.run(["tailscale","ip","-4"],capture_output=True,text=True,timeout=2,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        import ipaddress
        candidate=cp.stdout.strip().splitlines()[0]
        if ipaddress.ip_address(candidate) in ipaddress.ip_network("100.64.0.0/10"):
            return candidate
    except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):pass
    return None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8787)
    parser.add_argument("--bind",default="127.0.0.1",help="Bind to a single trusted interface; default loopback")
    parser.add_argument("--no-tailscale",action="store_true")
    args=parser.parse_args()
    services=[serve(args.bind,args.port)]
    ts=tailscale_ip() if not args.no_tailscale else None
    if ts and args.bind=="127.0.0.1":
        try:
            services.append(serve(ts,args.port))
        except OSError as exc:
            logging.warning("Tailscale address unavailable: %s",exc)
    threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in services]
    for t in threads:t.start()
    try:
        while True:time.sleep(4)
    except KeyboardInterrupt:
        for s in services:s.shutdown()

if __name__=="__main__": main()
