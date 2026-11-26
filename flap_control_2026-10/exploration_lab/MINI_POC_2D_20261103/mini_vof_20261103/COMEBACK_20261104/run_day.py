"""Bounded one-rank STAR tests, separate server/client, no foreign process mutations."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STOP = HERE / "STOP_REQUESTED"
LOCK = HERE / "CONTROLLER.lock"
CHECKPOINT = HERE.parent / "Q2D_NATIVE_A005_REMAINING49" / "VOF_checkpoint.sim"
FOIL = HERE.parent / "NIGHT_20261103" / "FOIL_MESH" / "mesh_3d.msh"
HASH = "ef36d8738b8c2efaa882c5da7953aef8f55477303bceb76076ceb91847cdf85c"
FLAG = subprocess.CREATE_NO_WINDOW
CLI = r"E:\Program Files\Siemens\21.04.009-R8\STAR-CCM+21.04.009-R8\star\lib\win64\clang20.1vc14.2-r8\lib\starccm+.exe"
PORT = 48863
FOREIGN_QUEUE = Path(r"E:\ntnu_mesh_optimization_20261030\nwar_automation_20261102\queue.sqlite")
READ = r"$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(starccm[+w]|star-ccm\+|smpd|mpiexec|impi)' } | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath) | ConvertTo-Json -Compress"
OWNER = "$ErrorActionPreference='Stop'; @(Get-NetTCPConnection -State Listen -LocalPort 48863 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique) | ConvertTo-Json -Compress"
STAGES = {
    "A05_SMOKE": dict(source=CHECKPOINT, expected_time=.05, steps=40),
    "B_KINEMATICS": dict(fresh=True, foil=True, moving=True, kinematics=True, expected_time=0, dt=.005, inner=1, amplitude=0, old_amplitude=0, steps=40),
    "I0_CALM_SMOKE": dict(fresh=True, foil=True, expected_time=0, amplitude=0, old_amplitude=0, steps=40),
}

def query(code):
    result = subprocess.run(["powershell", "-NoProfile", "-Command", code], capture_output=True,
                            text=True, check=True, timeout=25, creationflags=FLAG)
    value = json.loads(result.stdout.strip() or "[]")
    return value if isinstance(value, list) else [value]

def status(**value):
    # Dashboard publication is ancillary; native safety and checkpoint writes are independent.
    value["at"] = dt.datetime.now().astimezone().isoformat()
    payload = json.dumps(value, indent=2)
    tmp = HERE / f"DAY_STATUS.{os.getpid()}.{time.monotonic_ns()}.tmp"
    folder = Path(value.get("output", HERE))
    try:
        tmp.write_text(payload, encoding="utf8")
        for attempt in range(21):
            try:
                os.replace(tmp, HERE / "DAY_STATUS.json")
                for name in ("CONTROLLER_STATUS_PENDING.json", "STATUS_PUBLISH_WARNING.json"):
                    try:
                        (folder / name).unlink(missing_ok=True)
                    except OSError:
                        pass
                return
            except PermissionError:
                if attempt == 20:
                    raise
                time.sleep(.1)
    except OSError as error:
        # Keep the state alongside the owned run if Windows temporarily locks the shared JSON.
        # Never convert a dashboard file-sharing error into a solver stop request.
        try:
            (folder / "CONTROLLER_STATUS_PENDING.json").write_text(payload, encoding="utf8")
            (folder / "STATUS_PUBLISH_WARNING.json").write_text(json.dumps({"at": value["at"], "error": str(error), "native_solver_affected": False}, indent=2), encoding="utf8")
        except OSError:
            pass
        print("WARNING: dashboard status publication deferred: " + str(error), file=sys.stderr, flush=True)


def sha(path):
    import hashlib
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def independent_jobs():
    uri = FOREIGN_QUEUE.as_uri() + "?mode=ro"
    with sqlite3.connect(uri,uri=True,timeout=3) as conn:
        return conn.execute("SELECT case_id,status FROM jobs WHERE status IN ('queued','preflight','running','pausing')").fetchall()

def protected_idle():
    busy = independent_jobs()
    if busy:
        raise RuntimeError("Independent CFD queue has priority: " + str(busy))
    active = query(READ)
    if active:
        raise RuntimeError("Other STAR/MPI present: " + str([(p["Name"],p["ProcessId"]) for p in active]))
    if query(OWNER):
        raise RuntimeError("Dedicated port is occupied")
    if shutil.disk_usage(HERE).free < 7 * 2**30:
        raise RuntimeError("Less than 7 GiB free")

def cfd_owned_remain(owned):
    for _ in range(10):
        if not any(process["ProcessId"] in owned for process in query(READ)):
            return False
        time.sleep(1)
    return True


def _ensure_file_rotation(source):
    import importlib.util
    module_name = "_ntnu_flap_storage"
    path = Path("C:/Users/ThinkPad/Documents/ChatGPT/ntnu science/flap_storage/manager.py")
    try:
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        module.pin_source(source)
        module.ensure_running()
    except Exception as error:
        if source and re.fullmatch(r"CP_\d+_t[-+\d.]+\.sim", Path(source).name, re.I):
            raise RuntimeError("Cannot protect the requested restart checkpoint") from error
        print("WARNING: file rotation unavailable: " + str(error), file=sys.stderr, flush=True)


def new_job(stage, settings, protection=None, *, macro_source=None, mpi_cpu_indices=None, gpu=False):
    _ensure_file_rotation(settings.get("source"))
    eight_rank_stages = {"CALM_VOF_BENCH_CPU8", "CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE",
                         "CALM_VOF_NATIVE_FULL_BAND_ACTIVE_PLUS_MINUS_5"}
    if mpi_cpu_indices is not None:
        count = len(mpi_cpu_indices)
        if (count not in (2, 8) or len(set(mpi_cpu_indices)) != count or protection is None
                or (count == 8 and (gpu or stage not in eight_rank_stages))):
            raise ValueError("Unsupported Mini CPU affinity configuration")
    if STOP.exists():
        raise RuntimeError("Local stop requested")
    preflight = protection.preflight if protection else protected_idle
    preflight()
    if sha(CHECKPOINT) != HASH:
        raise RuntimeError("Source checkpoint SHA mismatch")
    source = settings.get("source")
    now = time.time()
    limit = int(settings.get("limit_seconds",720))
    out = Path(settings.get("run_root", HERE / "runs")) / (stage + "_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True)
    values = dict(authorization="COMEBACK_DAY_20261104", stage=stage, expected_cells=44442 if settings.get("foil") else 41280,
                  dt=.001, inner=20, amplitude=.05, old_amplitude=.05, damping_length=8, forcing_length=4,
                  pressure_tol=.01, pressure_urf=.5, wall_budget_s=max(60,limit-240), deadline_ms=int((now+limit)*1000),
                  stop_path=STOP.as_posix())
    values.update({k:v for k,v in settings.items() if k!="source"})
    if values.get("fresh"):
        values["mesh"] = (FOIL if settings.get("foil") else HERE.parent/"Q2D_NATIVE_A005_SMOKE50_FACEFIX"/"mesh_3d.msh").as_posix()
        if settings.get("mesh_override"):
            mesh = Path(settings["mesh_override"]).resolve()
            if not mesh.is_relative_to((HERE/"WALL_FUNCTIONS_AUDIT").resolve()) or sha(mesh)!=settings.get("mesh_override_sha256"):
                raise RuntimeError("Invalid wall mesh override")
            values["mesh"] = mesh.as_posix()
    props = "\n".join(f"{k}={str(v).lower() if isinstance(v,bool) else v}" for k,v in values.items())
    (out/"job.properties").write_text(props+"\n",encoding="ascii")
    macro_name = "VerifyComeback.java" if settings.get("verify") else "MiniVofStokes.java" if settings.get("stokes") else "MiniVofComeback.java"
    macro_source = HERE/macro_name if macro_source is None else Path(macro_source)
    (out/"job.json").write_text(json.dumps({**values,"input_sha256":sha(source) if source else None,
                                           "macro_sha256":sha(macro_source)},indent=2),encoding="utf8")
    if source:
        shutil.copy2(source,out/"input.sim")
        if sha(out/"input.sim")!=sha(source):
            raise RuntimeError("Checkpoint copy SHA mismatch")
    shutil.copy2(macro_source,out/macro_name)
    sys.path.insert(0,str(ROOT))
    import day_chain
    env = {**os.environ, **day_chain.LIC, "MINI_CASE_DIR":str(out), "COMEBACK_OWN_SESSION":"1"}
    server = None
    client = None
    owned = set()
    rank = None
    reason = ""
    began = time.perf_counter()
    rank_count = len(mpi_cpu_indices) if mpi_cpu_indices is not None else 1
    args = [CLI,"-server","-assignport",str(PORT),"-power","-np",str(rank_count),"-cpubind","off","-printpids"]
    if gpu:
        args += ["-gpgpu","auto:1","-require-gpgpu-compatibility"]
    args += ["-new"] if source is None else [str(out/"input.sim")]
    try:
        preflight()
        if settings.get("direct_batch"):
            if protection is None or mpi_cpu_indices is None or gpu:
                raise RuntimeError("Direct batch requires protected CPU affinity")
            batch_args = [arg for arg in args if arg != "-server"]
            batch_args[1:1] = ["-nbuserdir", str(out/"batch_profile"), "-batch", str(out/macro_name)]
            env["COMEBACK_OWN_SESSION"] = "0"
            bound = False
            launch_seconds = None
            with (out/"batch.log").open("w", encoding="utf8") as log:
                client = subprocess.Popen(batch_args, cwd=out, env=env, stdout=log,
                                          stderr=subprocess.STDOUT, creationflags=FLAG)
                owned.add(client.pid)
                status(stage=stage, solver_state="STOPPED", operation="LOADING",
                       client_pid=client.pid, output=str(out))
                while client.poll() is None:
                    proc = query(READ)
                    old = -1
                    while old != len(owned):
                        old = len(owned)
                        owned.update(p["ProcessId"] for p in proc if p["ParentProcessId"] in owned)
                    native = out/"native_status.json"
                    if not bound:
                        with (out/"batch.log").open(encoding="utf8", errors="replace") as stream:
                            head = stream.read(65536)
                        ranks = {int(index):int(pid) for index,pid in re.findall(
                            r"(?m)^Host ID \d+ Rank (\d+) on \S+ with process ID (\d+)\s*$", head)}
                        ranks.update({int(index):int(pid) for index,pid in re.findall(
                            r"(?m)^Process rank (\d+)\s+\S+\s+(\d+)\s*$", head)})
                        owned.update(ranks.values())
                        if len(ranks) == rank_count and 0 in ranks:
                            rank = ranks[0]
                            binding = protection.bind_native_ranks(ranks, mpi_cpu_indices)
                            (out/"NATIVE_MPI_BINDING.json").write_text(json.dumps(binding, indent=2), encoding="utf8")
                            launch_seconds = time.perf_counter()-began
                            bound = True
                        elif native.is_file() or time.perf_counter()-began > int(settings.get("startup_binding_timeout_s",240)):
                            STOP.write_text("Direct batch CPU binding not verified. Stop at physical boundary.", encoding="ascii")
                    protection.poll(owned, out, "CLIENT" if bound else "STARTUP")
                    if native.exists():
                        data = json.loads(native.read_text(encoding="utf8"))
                        age = max(0,time.time()-native.stat().st_mtime)
                        if age>180 and not STOP.exists():
                            STOP.write_text("Native heartbeat stale; request graceful stop.", encoding="ascii")
                        status(stage=stage, native_pid=rank, client_pid=client.pid, output=str(out),
                               solver_state=data["solver_state"], operation=data["operation"],
                               physical_time=data["time_s"], startup_s=launch_seconds, heartbeat_age_s=age)
                    if time.time() >= now+limit+45:
                        STOP.write_text("Direct batch exceeded deadline; preserve owned process.", encoding="ascii")
                        raise RuntimeError("Direct batch still active after deadline")
                    time.sleep(2)
                if client.returncode or not bound or cfd_owned_remain(owned):
                    raise RuntimeError(f"Direct STAR batch failed or left an owned process: exit {client.returncode}")
        else:
            with (out/"server.log").open("w",encoding="utf8") as log, (out/"client.log").open("w",encoding="utf8") as clog:
                server = subprocess.Popen(args,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=FLAG)
                owned.add(server.pid)
                status(stage=stage,solver_state="STOPPED",operation="LOADING",server_pid=server.pid,output=str(out))
                until = time.monotonic()+240
                while time.monotonic()<until and server.poll() is None:
                    if protection: protection.poll(owned,out,"STARTUP")
                    if STOP.exists():
                        reason="STOP requested during startup"
                    contents=(out/"server.log").read_text(encoding="utf8",errors="replace")
                    ranks={int(index):int(pid) for index,pid in re.findall(r"(?m)^Process rank (\d+)\s+\S+\s+(\d+)\s*$",contents)}
                    ranks.update({int(index):int(pid) for index,pid in re.findall(r"(?m)^Host ID \d+ Rank (\d+) on \S+ with process ID (\d+)\s*$",contents)})
                    owned.update(ranks.values())
                    if len(ranks)==rank_count and 0 in ranks:
                        rank=ranks[0]
                        if rank in query(OWNER):
                            break
                    time.sleep(2)
                if rank is None or rank not in query(OWNER):
                    raise RuntimeError("Owned native STAR listener not verified")
                launch_seconds=time.perf_counter()-began
                if protection:
                    if mpi_cpu_indices is None:
                        protection.bind_native(rank)
                    else:
                        binding=protection.bind_native_ranks(ranks,mpi_cpu_indices)
                        (out/"NATIVE_MPI_BINDING.json").write_text(json.dumps(binding,indent=2),encoding="utf8")
                    protection.poll(owned,out,"READY")
                    if STOP.exists(): reason="W06 protection requested stop"
                elif independent_jobs() or any("21.04.009-R8" not in (p.get("ExecutablePath") or "") for p in query(READ)):
                    reason="Independent CFD appeared during startup"
                    STOP.write_text(reason,encoding="ascii")
                if not reason:
                    client_args=[CLI,"-host","127.0.0.1","-port",str(PORT),"-nbuserdir",str(out/"client_profile"),"-batch",str(out/macro_name)]
                    client=subprocess.Popen(client_args,cwd=out,env=env,stdout=clog,stderr=subprocess.STDOUT,creationflags=FLAG)
                    owned.add(client.pid)
                while client is not None and client.poll() is None and time.time()<now+limit+45:
                    proc = query(READ)
                    is_new = True
                    while is_new:
                        old = len(owned)
                        owned.update(p["ProcessId"] for p in proc if p["ParentProcessId"] in owned)
                        is_new = len(owned)>old
                    foreign = [p for p in proc if p["ProcessId"] not in owned and "21.04.009-R8" not in (p.get("ExecutablePath") or "")]
                    if protection: protection.poll(owned,out,"CLIENT")
                    elif (foreign or independent_jobs()) and not STOP.exists():
                        STOP.write_text("Other STAR/MPI became active. Stop at physical step boundary.",encoding="ascii")
                    native = out/"native_status.json"
                    if native.exists():
                        data=json.loads(native.read_text(encoding="utf8"))
                        age=max(0,time.time()-native.stat().st_mtime)
                        cold_gpu = (gpu and stage in {"CALM_VOF_BENCH_GPU_WARM", "CALM_VOF_NATIVE_FULL_BAND_FIXED_STABILIZE"}
                                    and data.get("steps") == 0 and data.get("operation") == "SOLVING")
                        if age>(300 if cold_gpu else 180) and not STOP.exists():
                            STOP.write_text("Native heartbeat stale; request graceful stop.",encoding="ascii")
                        status(stage=stage,server_pid=server.pid,native_pid=rank,client_pid=client.pid,output=str(out),
                               solver_state=data["solver_state"],operation=data["operation"],physical_time=data["time_s"],
                               startup_s=launch_seconds,heartbeat_age_s=max(0,time.time()-native.stat().st_mtime))
                    time.sleep(2 if protection else 4)
                if client is not None and client.poll() is None:
                    STOP.write_text("Time limit reached. Preserve owned process if unresponsive.",encoding="ascii")
                    raise RuntimeError("Client still active after deadline; graceful stop requested")
                if server.poll() is None and rank in query(OWNER):
                    with (out/"close.log").open("w",encoding="utf8") as close_log:
                        subprocess.run([CLI,"-host","127.0.0.1","-port",str(PORT),"-nbuserdir",str(out/"close_profile"),
                                        "-batch",str(HERE/"CloseComeback.java")],cwd=out,env=env,stdout=close_log,
                                       stderr=subprocess.STDOUT,timeout=45,creationflags=FLAG,check=False)
                server.wait(timeout=30)
        if rank in query(OWNER):
            raise RuntimeError("Native rank still listening after close")
        if settings.get("verify"):
            if client is None or client.returncode or not (out/"REOPEN.json").exists():
                raise RuntimeError("Native checkpoint readback failed")
            status(stage=stage,solver_state="STOPPED",operation="CHECKPOINT_READBACK_WRITTEN",output=str(out))
            return {"status":"READBACK_WRITTEN","run_directory":str(out)}
        native_path=out/"SOLVE_STATUS.json"
        native=json.loads(native_path.read_text(encoding="utf8"))
        raw=out/("motion.csv" if values.get("kinematics") else "single_phase.csv" if values.get("single_phase") else "history.csv")
        with raw.open(newline="",encoding="utf8") as stream:
            rows=list(csv.DictReader(stream))
        if len(rows)!=native["steps"]:
            raise RuntimeError("Status/history length mismatch")
        timings=[float(r["solver_s"]) for r in rows][5:]
        cp=out/"FINAL.sim"
        result=dict(status=native["status"],samples=len(rows),startup_s=launch_seconds,
                    solver_step_median_s=statistics.median(timings) if timings else None,
                    solver_step_mean_s=statistics.mean(timings) if timings else None,
                    end_to_end_s=time.perf_counter()-began,dt_s=values["dt"],
                    checkpoint_sha256_input=sha(source) if source else None,
                    checkpoint=str(cp),checkpoint_sha256=sha(cp),state=native,
                    transport_ok=client is not None and client.returncode==0,
                    training_approved=False)
        (out/"DAY_RESULT.json").write_text(json.dumps(result,indent=2),encoding="utf8")
        status(stage=stage,solver_state="STOPPED",operation=native["status"],output=str(out),result=result)
        return result
    except Exception as error:
        still_active=any(p is not None and p.poll() is None for p in (server,client))
        if still_active:
            STOP.write_text("Review owned STAR. No new launch.",encoding="ascii")
        status(stage=stage,solver_state="HOLD" if still_active else "STOPPED",operation="HOLD",
               server_pid=server.pid if server else None,client_pid=client.pid if client else None,
               native_pid=rank,output=str(out),error=str(error))
        raise

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=[*STAGES,"status","preflight","stop"])
    args=parser.parse_args()
    if args.stage=="status":
        p=HERE/"DAY_STATUS.json"
        print(p.read_text(encoding="utf-8-sig") if p.exists() else "No run yet")
        return
    if args.stage=="stop":
        STOP.write_text("User stop; checked at a physical step boundary.",encoding="ascii")
        return
    if args.stage=="preflight":
        protected_idle()
        print("STAR/MPI idle")
        return
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        print(json.dumps(new_job(args.stage,STAGES[args.stage]),indent=2))
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()









