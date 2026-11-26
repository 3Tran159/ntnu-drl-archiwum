"""Independent, read-only live ramp ingestor for NTNU Project Control Center.
Reads controller metadata and bounded CSVs. Never opens checkpoints or writes to CFD.
"""
from __future__ import annotations
import csv
import ctypes
import datetime as dt
import io
import json
import logging
import math
import os
import re
import threading
import time
from pathlib import Path

CAMP = Path(r"F:\ntnu\flap_control\hydro_validation_2606_20261102")
CASES = CAMP / "cases" / "SP_C_split0_overset"
QUEUE = CAMP / "NIGHT_QUEUE_STATE.json"
STATUS = CAMP / "NIGHT_STATUS.json"
MAX_CSV = 10_000_000
MAX_JSON = 9_000_000
PRESSURE_THRESHOLD_PA = 12340.0
_CACHE = {"time": 0.0, "result": None}
_LOCK = threading.Lock()

def stable_bytes(path, cap):
    """A file is accepted only if its size and mtime are unchanged across read."""
    try:
        for _ in range(2):
            a = path.stat()
            if a.st_size > cap:
                return None
            with path.open("rb") as f:
                blob = f.read(cap + 1)
            b = path.stat()
            if len(blob) <= cap and a.st_size == b.st_size and a.st_mtime_ns == b.st_mtime_ns:
                return blob
            time.sleep(0.018)
    except (OSError, ValueError):
        return None
    return None

def read_json(path):
    b = stable_bytes(path, MAX_JSON)
    try:
        return json.loads(b.decode("utf-8-sig")) if b is not None else {}
    except (UnicodeError, ValueError, TypeError):
        return {}

def read_csv(path, max_rows=4500):
    b = stable_bytes(path, MAX_CSV)
    if b is None:
        return []
    try:
        content = b.decode("utf-8-sig")
        # Never ingest a partially written last CSV record.
        if content and not content.endswith(("\r", "\n")):
            content = content.rsplit("\n", 1)[0] + "\n" if "\n" in content else ""
        rows = list(csv.DictReader(io.StringIO(content)))
        rows = [row for row in rows if row and None not in row]
        if len(rows) > max_rows:
            # Downsample only for bounded plotting, never synthesize time points.
            stride = math.ceil(len(rows)/max_rows)
            rows = rows[::stride] + ([rows[-1]] if rows[-1] != rows[::stride][-1] else [])
        return rows
    except (UnicodeError, ValueError, csv.Error, IndexError):
        return []

def num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None

def get(row, *keys):
    for key in keys:
        if key in row:
            n = num(row[key])
            if n is not None:
                return n
    return None

def safe_output(raw):
    if not isinstance(raw, str) or not raw:
        return None
    try:
        p = Path(raw).resolve(strict=False)
        # Limit all job-driven reads to the specific campaign's cases tree.
        if not p.is_relative_to(CASES.resolve(strict=False)):
            return None
        if not re.match(r"^ramp_plus2_", p.name, re.I):
            return None
        return p
    except (ValueError, OSError):
        return None

def is_ramp_job(job):
    if not isinstance(job, dict):
        return False
    uid = str(job.get("experiment_id") or job.get("id") or "")
    return ("RAMP_" in uid.upper() or
            re.search(r"^RampPlus2", str(job.get("macro") or ""), re.I) is not None)

def select_experiment(queue):
    """Group actual controller jobs by experiment_id, no hardcoded output folder."""
    jobs = queue.get("jobs") if isinstance(queue, dict) else None
    entries = list(jobs.values()) if isinstance(jobs, dict) else []
    active = queue.get("active") if isinstance(queue, dict) else None
    if isinstance(active, dict):
        entries.append(active)
    entries = [j for j in entries if is_ramp_job(j) and safe_output(j.get("output"))]
    if not entries:
        return {"experiment_id": None, "jobs": [], "active": None}
    live = active if isinstance(active, dict) and is_ramp_job(active) and safe_output(active.get("output")) else None
    exp = str((live or max(entries, key=lambda j: str(j.get("at") or j.get("run_id") or ""))).get("experiment_id") or "")
    if not exp:
        exp = str((live or entries[-1]).get("id") or "").split("_SMOKE")[0].split("_RUN")[0]
    selected = [j for j in entries if str(j.get("experiment_id") or "") == exp or
                (not j.get("experiment_id") and str(j.get("id") or "").startswith(exp))]
    # Collapse duplicate entries: active replaces matching historical job.
    unique = {}
    for j in selected:
        unique[str(safe_output(j.get("output"))).lower()] = j
    selected = sorted(unique.values(), key=lambda j: (str(j.get("at") or ""), str(j.get("run_id") or "")))
    return {"experiment_id": exp, "jobs": selected[-12:], "active": live if live and str(live.get("experiment_id") or "") == exp else None}

def rows_for_job(job):
    path = safe_output(job.get("output"))
    if not path:
        return [], None
    hist = path / "history.csv"
    entries = []
    for raw in read_csv(hist):
        t = get(raw, "time_s", "Time", "physical_time_s")
        if t is None:
            continue
        angle = get(raw, "flap_angle_deg", "target_angle_deg", "command_angle_deg")
        actual = get(raw, "measured_angle_deg", "actual_angle_deg")
        speed = get(raw, "flap_angular_velocity_deg_s", "angular_rate_deg_s")
        moment = get(raw, "Mh_Nm", "hinge_moment_Nm")
        # Moment sign convention not audited: signed product, not actuator demand.
        power = moment * speed * math.pi / 180 if moment is not None and speed is not None else None
        row = {
            "t": t, "step": get(raw, "step", "TimeStep"), "iteration": get(raw, "native_iteration", "iteration"),
            "angle": angle, "actual_angle": actual, "rate": speed,
            "CL": get(raw, "CL_hydro", "CL"), "CD": get(raw, "CD"),
            "Fx": get(raw, "Fx_N", "Fx"), "Fz": get(raw, "Fz_N", "Fz"), "Mh": moment,
            "pabs": get(raw, "p_absolute_min_Pa"), "mass": get(raw, "mass_imbalance_relative"),
            "cav_margin": get(raw, "cavitation_margin_Pa"),
            "overset": get(raw, "overset_error_cells"), "difficult": get(raw, "difficult_interpolation_cells"),
            "k_floor": get(raw, "k_floor_cells"), "omega_floor": get(raw, "omega_floor_cells"),
            "viscosity_ratio": get(raw, "max_turbulent_viscosity_ratio"),
            "min_quality": get(raw, "min_cell_quality"), "min_volume": get(raw, "min_volume_m3"),
            "face_validity": get(raw, "min_face_validity"), "yplus_max": get(raw, "yplus_max"),
            "solver_step_seconds": get(raw, "solver_step_seconds"),
            "Pmech": power,
            "segment": str(job.get("id") or path.name),
            "source": str(hist),
        }
        entries.append(row)
    return entries, (hist.stat().st_mtime if hist.is_file() else None)

def pid_alive(pid):
    """Non-invasive read of Windows process liveness: no signals or solver API."""
    pid = num(pid)
    if os.name != "nt" or pid is None or pid <= 0:
        return False
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        code = ctypes.c_ulong(0)
        return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259
    finally:
        k.CloseHandle(h)

def classify(job_state, queue_state, source_age, pid_ok, has_rows):
    """Conservative. RUNNING needs fresh numerical output AND a live owned PID."""
    js, qs = str(job_state or "").lower(), str(queue_state or "").lower()
    if any(x in js for x in ("failed", "error", "crashed")) or any(x in qs for x in ("failed", "fatal")):
        return "FAILED", "Controller reports failure."
    if any(x in js for x in ("completed", "complete", "finished", "success")):
        return "COMPLETE", "Controller completed the segment; scientific acceptance is separate."
    if any(x in js for x in ("hold", "pause", "blocked")) or any(x in qs for x in ("hold", "paused")):
        return "HOLD", "Controller explicitly held the experiment."
    if not has_rows or source_age is None:
        return "HOLD", "No complete recorded ramp samples yet."
    if source_age > 70:
        return "STALE", "Ramp history has not changed for over 70 seconds."
    if pid_ok and source_age <= 40 and js in ("active", "running", "in_progress"):
        return "RUNNING", "Owned process exists and recorded CSV is fresh."
    return "HOLD", "No fresh, independently confirmed progress."

def residuals_for(folder):
    out = {}
    if not folder:
        return out
    for f in sorted(folder.glob("residual_readback_*.csv")):
        data = read_csv(f, max_rows=650)
        if not data:
            continue
        keys = [k for k in data[0] if k not in ("Iteration", "iteration", "Time")]
        channel = f.stem.replace("residual_readback_", "")
        if not keys:
            continue
        values = []
        for line in data:
            x = get(line, "Iteration", "iteration")
            y = get(line, keys[0])
            if x is not None and y is not None:
                values.append({"x": x, "y": y})
        if values:
            out[channel] = {"points": values, "source": str(f), "updated_at": dt.datetime.fromtimestamp(f.stat().st_mtime, dt.timezone.utc).isoformat(),
                            "axis": "solver iteration (not physical time)"}
    return out

def residuals_from_log(raw_path):
    """Read only a bounded tail of the active STAR console log; no solver API."""
    if not isinstance(raw_path, str) or not raw_path:
        return {}
    try:
        path = Path(raw_path).resolve(strict=False)
        if not path.is_relative_to((CAMP / "runs").resolve(strict=False)):
            return {}
        if not path.name.lower().startswith(("rampplus2run_", "rampplus2smoke_")) or path.suffix.lower() != ".log":
            return {}
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > 450_000:
                fh.seek(-450_000, os.SEEK_END)
            blob = fh.read(450_000)
        raw = blob.decode("utf-8", errors="replace")
        lines = raw.splitlines()
        if size > 450_000:
            lines = lines[1:]
        if not raw.endswith(("\n", "\r")) and lines:
            lines = lines[:-1]
        pattern = re.compile(r"^\s*(\d{3,})\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)\s+((?:\d+\.?\d*|\.\d+)[eE][+-]?\d+)")
        points = {}
        for line in lines:
            match = pattern.match(line)
            if not match:
                continue
            it = int(match.group(1))
            vals = [num(x) for x in match.groups()[1:]]
            if all(x is not None and x >= 0 for x in vals):
                points[it] = vals
        if not points:
            return {}
        names = ["Continuity","X-momentum","Y-momentum","Z-momentum","Tke","Sdr"]
        keys = sorted(points)[-400:]
        stamp = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
        return {name:{"points":[{"x":float(it),"y":points[it][i]} for it in keys],
                      "source":str(path),"updated_at":stamp,
                      "axis":"solver iteration (not physical time)",
                      "live_log":True}
                for i,name in enumerate(names)}
    except (OSError,ValueError,TypeError) as exc:
        logging.warning("Ramp log residual source unavailable: %s",exc)
        return {}

def build_payload(queue=None, status=None, now=None):
    now = time.time() if now is None else now
    queue = read_json(QUEUE) if queue is None else queue
    status = read_json(STATUS) if status is None else status
    selection = select_experiment(queue)
    jobs = selection["jobs"]
    active = selection["active"]
    combined = {}
    latest_mtime = None
    segment_details = []
    for job in jobs:
        path = safe_output(job.get("output"))
        rows, mtime = rows_for_job(job)
        for row in rows:
            # Time identifies a physical sample even if native step counters reset.
            # Newer segment wins on overlap. No interpolation, no fabricated endpoints.
            combined[round(row["t"], 9)] = row
        if mtime is not None:
            latest_mtime = mtime if latest_mtime is None else max(latest_mtime, mtime)
        segment_details.append({"id": job.get("id"), "state": job.get("state"),
                                "path": str(path), "history": str(path / "history.csv"),
                                "rows": len(rows), "mtime": mtime,
                                "at": job.get("at"), "run_id": job.get("run_id")})
    history = sorted(combined.values(), key=lambda row: row["t"])
    if len(history) > 8000:
        k = math.ceil(len(history)/8000)
        history = history[::k] + ([history[-1]] if history[-1] is not history[::k][-1] else [])
    current = history[-1] if history else {}
    current_segment = active or (jobs[-1] if jobs else None)
    active_output = safe_output(current_segment.get("output")) if current_segment else None
    modified_age = max(0, now - latest_mtime) if latest_mtime is not None else None
    process = pid_alive(current_segment.get("pid")) if current_segment else False
    state, reason = classify((current_segment or {}).get("state"),
                             queue.get("queue_state") if isinstance(queue, dict) else None,
                             modified_age, process, bool(history))
    run_id = selection["experiment_id"]
    # This known validated plan is explicitly tied to the named +2° S5 experiment.
    known_profile = bool(run_id and "PLUS2_S5" in run_id.upper())
    profile = {"start_s": .650, "end_s": .850, "target_deg": 2.0, "dt_s": .002,
               "name": "quintic smoothstep", "source": "experiment specification"} if known_profile else None
    if profile and current.get("t") is not None:
        t = current["t"]
        progress = max(0., min(1., (t-profile["start_s"])/(profile["end_s"]-profile["start_s"])))
        phase = "PRE-RAMP" if t < profile["start_s"] else "RAMP" if t < profile["end_s"] else "HOLD"
    else:
        progress, phase = None, "UNKNOWN"
    checkpoint = None
    ckmeta = status.get("latest_owned_checkpoint") if isinstance(status, dict) else None
    if isinstance(ckmeta, dict):
        checkpoint = {"path": ckmeta.get("path"), "saved_time_s": ckmeta.get("saved_time_s"),
                      "save_complete": ckmeta.get("native_save_complete"),
                      "source": str(STATUS)}
    elif isinstance(ckmeta, str):
        checkpoint = {"path": ckmeta, "source": str(STATUS)}
    if current_segment and current_segment.get("checkpoints"):
        candidates = current_segment["checkpoints"]
        if isinstance(candidates, list) and candidates:
            last = candidates[-1]
            if isinstance(last, dict) and last.get("path"):
                checkpoint = {"path": last["path"], "source": str(QUEUE),
                              "save_complete": last.get("native_save_complete")}
    if not checkpoint and isinstance(queue.get("checkpoint_integrity"), dict):
        checkpoint = {"path": queue["checkpoint_integrity"].get("path"),
                      "source": str(QUEUE)}
    errors = []
    for col in ("CL", "CD", "Fx", "Fz", "Mh", "pabs", "mass", "angle", "actual_angle", "rate"):
        if current and current.get(col) is None:
            errors.append(col)
    latest_source = current.get("source") if current else None
    live_residuals = residuals_from_log((current_segment or {}).get("log"))
    data = {
        "experiment_id": run_id, "state": state, "reason": reason,
        "phase": phase, "progress": progress, "profile": profile,
        "current": current, "history": history, "rows": len(history),
        "segments": segment_details, "active_job": {
            "id": (current_segment or {}).get("id"), "state": (current_segment or {}).get("state"),
            "pid": (current_segment or {}).get("pid"), "output": str(active_output) if active_output else None,
            "macro": (current_segment or {}).get("macro"),
            "is_live_process": process,
        },
        "source_file": latest_source,
        "source_updated_at": dt.datetime.fromtimestamp(latest_mtime, dt.timezone.utc).isoformat() if latest_mtime else None,
        "source_age_s": round(modified_age, 1) if modified_age is not None else None,
        "server_time": dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
        "checkpoint": checkpoint,
        "threshold_pa": PRESSURE_THRESHOLD_PA,
        "pressure_margin_pa": (current["pabs"]-PRESSURE_THRESHOLD_PA) if current.get("pabs") is not None else None,
        "missing_signals": errors,
        "power_convention": "Signed Mh[recorded] × angular velocity in rad/s. Hinge moment orientation is unverified; not electric actuator power or a craft energy budget.",
        "residuals": live_residuals if live_residuals else residuals_for(active_output),
        "residuals_note": ("Latest native STAR log iterations; not mapped to physical-time steps." if live_residuals else
                           "Saved residual readback snapshot; not synchronized to physical time."),
        "read_only": True,
    }
    return data

def snapshot():
    now = time.time()
    with _LOCK:
        if _CACHE["result"] is not None and now - _CACHE["time"] < 3:
            return _CACHE["result"]
    try:
        output = build_payload(now=now)
    except Exception:
        logging.exception("Ramp reader failure")
        output = {"experiment_id": None, "state": "STALE", "reason": "Ramp reader unavailable",
                  "history": [], "rows": 0, "segments": [], "read_only": True}
    with _LOCK:
        _CACHE.update({"time": time.time(), "result": output})
    return output
