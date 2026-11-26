from pathlib import Path
import json
import os
import shutil
import csv
import sqlite3
import statistics
import sys
import time

D=Path(__file__).resolve().parent
OUT=D.parent
ROOT=OUT.parent
sys.path.insert(0,str(OUT.parents[2]))
import stokes_coexistence as coex
from run_day import HERE, LOCK, STOP, OWNER, READ, FOREIGN_QUEUE, new_job, query, sha

sys.path.insert(0,r"F:\ntnu\flap_control\hydro_validation_2606_20261102\tools")
from benchmark_telemetry import topology


class ProtectedTwoRanks(coex.W06Protection):
    def check_foreign(self, owned):
        processes=query(READ)
        known={p["ProcessId"] for p in processes if p["ProcessId"] in coex.EXPECTED
               and "21.02.007-R8" in (p.get("ExecutablePath") or "")}
        if not {coex.RANK,coex.W06_LAUNCHER}<=known or independent_jobs()!=[("W06","running")]:
            raise RuntimeError("W06 identity or independent CFD queue changed")
        self.unowned_pids=sorted(p["ProcessId"] for p in processes
                                if p["ProcessId"] not in known and p["ProcessId"] not in owned)

    def preflight(self):
        self.check_foreign(set())
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        snapshot=coex.host_snapshot()
        initial={p["pid"]:p for p in self.snapshot["processes"]}
        if snapshot["free_GiB"]<8 or any(p["mask"]&coex.MASK or p["birth"]!=initial[p["pid"]]["birth"]
                                      for p in snapshot["processes"]):
            raise RuntimeError("W06 identity, E-core overlap, or RAM preflight failure")

    def bind_native_ranks(self, ranks, cpus):
        rows=[]
        for i,cpu in enumerate(cpus):
            pid=ranks[i]
            mask=1<<cpu
            row=query(f"""
$ErrorActionPreference='Stop'
$c=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'
if($c.Name -ne 'star-ccm+.exe' -or $c.ExecutablePath -notlike '*21.04.009-R8*'){{throw 'Not a Mini 2606 rank'}}
$p=Get-Process -Id {pid}
$p.ProcessorAffinity=[IntPtr]{mask}
[pscustomobject]@{{pid=$p.Id;mask=$p.ProcessorAffinity.ToInt64()}}|ConvertTo-Json -Compress
""")[0]
            if row["mask"]!=mask:
                raise RuntimeError("Mini rank affinity readback failed")
            rows.append(dict(rank=i,logical_cpu=cpu,**row))
            self.process_ids.add(pid)
        return rows


class ResourceGuard(ProtectedTwoRanks):
    baseline_s=1.6459431500006758

    def __init__(self):
        super().__init__()
        self.watch=None
        self.last_poll=0
        self.last_sample=None

    def resources(self):
        return query(r"""
$os=Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{free_GiB=$os.FreePhysicalMemory/1MB}|ConvertTo-Json -Compress
""")[0]

    def preflight(self):
        if query(OWNER) or shutil.disk_usage(HERE).free<7*2**30:
            raise RuntimeError("Mini port occupied or insufficient disk space")
        if self.resources()["free_GiB"]<8:
            raise RuntimeError("Insufficient free RAM")
        self.observe_w06()

    def observe_w06(self):
        with sqlite3.connect(FOREIGN_QUEUE.as_uri()+"?mode=ro",uri=True,timeout=3) as db:
            jobs=db.execute("SELECT folder FROM jobs WHERE case_id='W06' AND status='running'").fetchall()
        if not jobs:
            return
        if len(jobs)!=1:
            raise RuntimeError("Multiple W06 jobs are simultaneously running")
        folder=Path(jobs[0][0])
        file=folder/"history.csv"
        if not file.is_file() or time.time()-file.stat().st_mtime>12:
            return
        log=folder/"star.log"
        if log.is_file():
            with log.open("rb") as f:
                import re
                ids=set(int(p) for p in re.findall(rb"(?m)^Process rank \d+\s+\S+\s+(\d+)\s*$",f.read(65536)))
            if ids:
                arg=",".join(str(p) for p in sorted(ids))
                masks=query(f"(Get-Process -Id {arg} -ErrorAction SilentlyContinue | ForEach-Object {{$_.ProcessorAffinity.ToInt64()}}) | ConvertTo-Json -Compress")
                if any(mask & coex.MASK for mask in masks):
                    raise RuntimeError("Active W06 solver affinity overlaps the selected Mini E-cores")
        with file.open("rb") as f:
            f.seek(0,2)
            f.seek(max(0,f.tell()-18000))
            rows=f.read().decode("utf8",errors="replace").splitlines()[1:]
        steps=[]
        for row in rows:
            values=row.split(",")
            try:
                steps.append((int(values[1]),float(values[2])))
            except (ValueError,IndexError):
                continue
        if len(steps)<8:
            return
        recent=steps[-8:]
        sample=(str(folder),recent[-1][0])
        if sample==self.last_sample or any(b[0]!=a[0]+1 or b[1]<=a[1] for a,b in zip(recent,recent[1:])):
            return
        self.last_sample=sample
        seconds=statistics.median(b[1]-a[1] for a,b in zip(recent,recent[1:]))
        slowdown=seconds/self.baseline_s-1
        self.peak=max(self.peak,slowdown)
        if self.watch:
            with self.watch.open("a",encoding="ascii",newline="") as f:
                csv.writer(f).writerow((time.strftime("%H:%M:%S"),sample[1],seconds,slowdown))
        if slowdown>.15:
            raise RuntimeError(f"W06 seven-step median slower by {slowdown:.1%}")

    def poll(self, owned, out, phase):
        if self.stopped or time.monotonic()-self.last_poll<5:
            return
        self.last_poll=time.monotonic()
        try:
            if self.resources()["free_GiB"]<8:
                raise RuntimeError("Insufficient free RAM")
            self.observe_w06()
        except Exception as exc:
            self.stopped=str(exc)
            if not STOP.exists():
                STOP.write_text(self.stopped,encoding="utf8")

def main():
    output=D/"TWO_E_COEX_RESULT.json"
    original=json.loads((D/"RESULT.json").read_text())
    retry=json.loads((D/"RETRY_RESULT.json").read_text())
    status=json.loads((HERE/"DAY_STATUS.json").read_text())
    marker="An independent solver job became active"
    if (output.exists() or not STOP.exists() or STOP.read_text().strip()!=marker
        or json.loads((D/"TWO_E_RESULT.json").read_text())["status"]!="HOLD" or retry["status"]!="HOLD"
        or status["solver_state"]!="STOPPED" or status["stage"]!="MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_IDLE_W06"):
        raise RuntimeError("Protected two-rank resume preflight blocked")
    prefix=Path(original["checkpoint"]).parent
    source=Path(r"T:\FLAPS_ARCHIVE\SEALED_GAP_2D_U18_20261104\SHARP_SEALED_FIXED_0P600S.sim")
    if (sha(source)!=original["checkpoint_sha256_input"] or not (prefix/"fixed_history.csv").is_file()
        or not (prefix/"fixed_windows.csv").is_file()):
        raise RuntimeError("Saved sharp sealed checkpoint or force history mismatch")
    mesh=json.loads((ROOT/"SEALED_SHARP_MATCHED_OUTER"/"MESH_AUDIT.json").read_text())
    topo=topology()
    classes={r["efficiency_class"] for r in topo}
    if len(classes)<2:
        raise RuntimeError("Windows did not identify distinct performance and efficiency classes")
    w06=query("(Get-Process -Id 18156,12224 -ErrorAction SilentlyContinue | ForEach-Object {$_.ProcessorAffinity.ToInt64()}) | ConvertTo-Json -Compress")
    mask=0
    for value in w06:
        mask|=value
    e=sorted(r["logical_cpu"] for r in topo if r["group"]==0 and r["efficiency_class"]==min(classes)
             and not (mask & (1<<r["logical_cpu"])))
    if len(e)<2:
        raise RuntimeError("Two unshared E-cores are unavailable")
    cpus=e[:2]
    coex.MASK=sum(1<<cpu for cpu in cpus)
    coex.W06Protection=ProtectedTwoRanks
    with LOCK.open("x",encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        guard=ResourceGuard()
        guard.watch=D/"TWO_E_COEX_W06_WATCH.csv"
        guard.preflight()
        with guard.watch.open("x",encoding="ascii") as f:
            f.write("time,W06_step,median_step_s,slowdown_fraction\n")
        archived_stop=D/"STOP_W06_QUEUE_PRESENCE_ARCHIVED.txt"
        if archived_stop.exists() or STOP.read_text().strip()!=marker:
            raise RuntimeError("Unexpected Mini stop marker")
        STOP.rename(archived_stop)
        coex.save(output,dict(status="RUNNING",checkpoint_source=str(source),initial_time_s=.6,
                              cpu_indices=cpus,mpi_ranks=2))
        result=new_job("MATCHED_FIXED_SHARP_SEALED_RESUME0600_TWO_E_COEX",dict(
            source=source,stokes=True,foil=True,moving=True,single_phase=True,
            coarse_2d_active=True,flow_cycle=True,expected_cells=mesh["cells"],
            expected_time=.6,amplitude=0,old_amplitude=0,inner=20,u_diagnostic_m_s=18,
            dt=.00025,steps=800,fixed_protocol=True,seeded_single_phase=True,
            fixed_from_unsteady=True,restore_fixed_history=True,
            fixed_prefix_directory=prefix.as_posix(),after_fixed_motion=True,limit_seconds=5600),
            protection=guard,macro_source=D/"MiniVofStokes.java",mpi_cpu_indices=cpus)
        case=Path(result["checkpoint"]).parent
        result["fixed"]=json.loads((case/"FIXED_PROTOCOL.json").read_text())
        result["W06"]=dict(mode="measured_resource_protection",peak=guard.peak,stop=guard.stopped)
        result["cpu_indices"]=cpus
        coex.save(output,result)
    except Exception as e:
        coex.save(output,dict(status="HOLD",error=str(e),cpu_indices=cpus))
        raise
    finally:
        LOCK.unlink()

if __name__=="__main__":
    main()

